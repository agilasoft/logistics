# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

from datetime import timedelta
from typing import Optional

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, get_datetime, now_datetime

from logistics.time_sensitive.sla import compute_sla_status, get_at_risk_hours_for_case
from logistics.time_sensitive.notifications import notify_case_event
from logistics.utils.virtual_linked_services_view import build_linked_services_view_for_booking


ALLOWED_TRANSITIONS = {
	"Draft": {"Triage", "Activated", "Cancelled"},
	"Triage": {"Activated", "On Hold", "Cancelled"},
	"Activated": {"In Execution", "On Hold", "Cancelled"},
	"In Execution": {"Delivered", "On Hold", "Cancelled"},
	"Delivered": {"Closed"},
	"On Hold": {"Triage", "Activated", "In Execution", "Cancelled"},
	"Closed": set(),
	"Cancelled": set(),
}

ACTIVE_STATUSES = ("Activated", "In Execution", "On Hold")

SERVICE_TYPE_TO_DOCTYPE = {
	"Air": "Air Booking",
	"Sea": "Sea Booking",
	"Transport": "Transport Order",
	"Customs": "Declaration Order",
	"Warehousing": "VAS Order",
	"Cross-Docking": "Cross-Docking Order",
	"On-Demand Last Mile": "ODDS Order",
}


class TimeSensitiveCase(Document):
	"""Time Sensitive Case with an editable virtual ``linked_services`` grid (Sales Quote pattern)."""

	def __setup__(self):
		"""Keep virtual ``linked_services`` initialised; honour desk grid rows on save."""
		self._stage_linked_services_from_form()

	@property
	def linked_services(self):
		"""Live view of Linked Service documents owned by or shared with this case.

		Prefer ``__dict__`` when present so Frappe's computed Table wrapper +
		``LazyDocument.append`` (full-page printview) does not RecursionError.
		"""
		if self.flags.get("_linked_services_from_form"):
			return self.__dict__.get("linked_services") or []
		if "linked_services" in self.__dict__:
			rows = self.__dict__["linked_services"]
			if rows and any(getattr(r, "__islocal", None) for r in rows):
				self.flags._linked_services_from_form = True
				return rows
			if not rows and getattr(self, "name", None) and not getattr(self, "__islocal", False):
				del self.__dict__["linked_services"]
			else:
				return rows
		if self.flags.get("_linked_services_view_cached"):
			# Cache may be stale after API create/link; rebuild from Linked Service docs.
			if getattr(self, "name", None) and not getattr(self, "__islocal", False):
				value = self._build_linked_services_view()
				self.__dict__["linked_services"] = value
				return value
			return []
		value = self._build_linked_services_view()
		self.__dict__["linked_services"] = value
		self.flags._linked_services_view_cached = True
		return value

	def _build_linked_services_view(self):
		if not getattr(self, "name", None) or getattr(self, "__islocal", False):
			return []
		return build_linked_services_view_for_booking(self.doctype, self.name)

	def _drop_virtual_linked_services_rows(self):
		"""Clear desk grid rows after sync; source of truth is ``Linked Service`` documents."""
		self.flags._linked_services_from_form = False
		self.flags._linked_services_view_cached = False
		self.__dict__["linked_services"] = []

	def _invalidate_linked_services_view(self):
		"""Drop stale virtual-grid cache without staging an intentional empty form."""
		self.flags._linked_services_from_form = False
		self.flags._linked_services_view_cached = False
		if "linked_services" in self.__dict__:
			del self.__dict__["linked_services"]

	def _stage_linked_services_from_form(self):
		"""Honour desk/API grid rows on save, including an intentional empty grid."""
		if "linked_services" not in self.__dict__:
			return
		if self.__dict__.get("linked_services") is None:
			self.__dict__["linked_services"] = []
		if not self.flags.get("_linked_services_view_cached"):
			self.flags._linked_services_from_form = True

	def _honour_linked_services_form_rows(self):
		self._stage_linked_services_from_form()

	def validate(self):
		self._honour_linked_services_form_rows()
		self._stamp_lifecycle_timestamps()
		self._apply_case_type_defaults()
		self._validate_status_transition()
		self._validate_activation_requirements()
		self._recalc_charge_amounts()
		self._derive_sla_status()

	def before_insert(self):
		self.append_event("Created", _("Case created"), severity="informational", is_system=1)

	def after_insert(self):
		self._create_job_number_if_needed()
		self._drop_virtual_linked_services_rows()

	def on_update(self):
		self._drop_virtual_linked_services_rows()
		if self.has_value_changed("status"):
			self._on_status_changed()
		if self.has_value_changed("coordinator") and self.coordinator:
			notify_case_event(
				self,
				event_type="Handoff",
				subject=_("Coordinator assigned: {0}").format(self.name),
				message=_("You are now coordinator for Time Sensitive Case {0}.").format(self.name),
				severity="informational",
				recipients=[self.coordinator],
			)
		if self.status in ACTIVE_STATUSES or self.has_value_changed("sales_quote"):
			self.stamp_attached_documents()

	def on_submit(self):
		if self.status in ("Draft", "Triage"):
			self.db_set("status", "Activated", update_modified=False)
			if not self.activated_on:
				self.db_set("activated_on", now_datetime(), update_modified=False)
			self.append_event("Activated", _("Case submitted and activated"), severity="impending", is_system=1, persist=True)
			notify_case_event(
				self,
				event_type="Activation",
				subject=_("Time Sensitive Case activated: {0}").format(self.name),
				message=self._alert_body(_("Case activated")),
				severity="impending",
			)
			self.stamp_attached_documents()

	def append_event(
		self,
		event_type: str,
		message: str,
		*,
		severity: str = "informational",
		linked_doctype: Optional[str] = None,
		linked_name: Optional[str] = None,
		is_system: int = 0,
		persist: bool = False,
	):
		row = {
			"event_datetime": now_datetime(),
			"event_type": event_type,
			"severity": severity,
			"user": frappe.session.user,
			"message": message,
			"linked_doctype": linked_doctype,
			"linked_name": linked_name,
			"is_system": cint(is_system),
		}
		self.append("events", row)
		if persist and not self.is_new():
			# Reload and append so submit-time events survive without full re-validate recursion
			try:
				fresh = frappe.get_doc("Time Sensitive Case", self.name)
				fresh.append("events", row)
				fresh.flags.ignore_validate = True
				fresh.flags.ignore_permissions = True
				fresh.save()
			except Exception:
				frappe.log_error(frappe.get_traceback(), "time_sensitive.append_event.persist")

	def stamp_attached_documents(self):
		"""Push time-sensitive identifiers and empty Sales Quote onto linked operational docs."""
		from logistics.time_sensitive.propagation import stamp_document_from_case

		from logistics.time_sensitive.service_linking import get_case_linked_services
		from logistics.utils.linked_service_usage import get_usages_for_linked_service

		for linked in get_case_linked_services(self):
			for usage in get_usages_for_linked_service(linked.name):
				doctype = usage.get("used_on_doctype")
				docname = usage.get("used_on_name")
				if not doctype or not docname or doctype == self.doctype:
					continue
				try:
					stamp_document_from_case(doctype, docname, self)
				except Exception:
					frappe.log_error(
						title="Time Sensitive Case stamp failed",
						message=f"{doctype} {docname}",
					)

	def _apply_case_type_defaults(self):
		if not self.case_type:
			return
		ct = frappe.get_cached_doc("Time Sensitive Case Type", self.case_type)
		if not self.severity and ct.default_severity:
			self.severity = ct.default_severity
		if not self.at_risk_hours:
			self.at_risk_hours = cint(ct.default_at_risk_hours) or 4
		if self.breach_grace_minutes is None:
			self.breach_grace_minutes = cint(ct.default_breach_grace_minutes) or 0
		if not self.milestone_template and ct.milestone_template:
			self.milestone_template = ct.milestone_template
		if not self.document_list_template and ct.document_list_template:
			self.document_list_template = ct.document_list_template
		if self.status in ("Draft", "Triage", "Activated") and self.activated_on and not self.response_due_on:
			mins = cint(ct.default_response_minutes) or 15
			self.response_due_on = get_datetime(self.activated_on) + timedelta(minutes=mins)

	def _validate_status_transition(self):
		if self.is_new():
			return
		prev = self.get_db_value("status")
		if not prev or prev == self.status:
			return
		allowed = ALLOWED_TRANSITIONS.get(prev, set())
		if self.status not in allowed:
			frappe.throw(
				_("Cannot move Time Sensitive Case from {0} to {1}.").format(prev, self.status)
			)

	def _validate_activation_requirements(self):
		if self.status not in ("Activated", "In Execution"):
			return
		missing = []
		if not self.coordinator:
			missing.append(_("Coordinator"))
		if not self.critical_deadline:
			missing.append(_("Critical Deadline"))
		if not (self.contact_24x7_name or self.contact_24x7_phone or self.contact_24x7_email):
			missing.append(_("24/7 Contact"))
		from logistics.time_sensitive.service_linking import get_case_linked_services

		if not get_case_linked_services(self):
			missing.append(_("at least one Linked Service"))
		if missing:
			frappe.throw(
				_("Cannot activate case without: {0}").format(", ".join(missing))
			)

	def _recalc_charge_amounts(self):
		for row in self.get("charges") or []:
			if row.charge_scope == "Linked" and not row.linked_service:
				frappe.throw(_("Linked charges require a Linked Service."))
			row.amount = flt(row.qty or 0) * flt(row.rate or 0)

	def _derive_sla_status(self):
		if self.status in ("Delivered", "Closed"):
			self.sla_status = "Completed"
			return
		if self.status == "Cancelled":
			return
		at_risk = get_at_risk_hours_for_case(self)
		grace = cint(self.breach_grace_minutes or 0)
		self.sla_status = compute_sla_status(
			self.critical_deadline,
			at_risk_hours=at_risk,
			breach_grace_minutes=grace,
			now=now_datetime(),
		)

	def _stamp_lifecycle_timestamps(self):
		now = now_datetime()
		if self.status in ("Activated", "In Execution") and not self.activated_on:
			self.activated_on = now
		if self.status == "Delivered" and not self.delivered_on:
			self.delivered_on = now
		if self.status == "Closed" and not self.closed_on:
			self.closed_on = now

	def _on_status_changed(self):
		status = self.status
		if status == "Activated":
			self.append_event("Activated", _("Case activated"), severity="impending", is_system=1)
			notify_case_event(
				self,
				event_type="Activation",
				subject=_("Time Sensitive Case activated: {0}").format(self.name),
				message=self._alert_body(_("Case activated")),
				severity="impending",
			)
		elif status == "Delivered":
			self.append_event("Delivered", _("Critical outcome confirmed"), severity="informational", is_system=1)
			notify_case_event(
				self,
				event_type="Delivered",
				subject=_("Time Sensitive Case delivered: {0}").format(self.name),
				message=self._alert_body(_("Case delivered")),
				severity="informational",
			)
		elif status == "Closed":
			self.append_event("Closed", _("Case closed"), severity="informational", is_system=1)

	def _create_job_number_if_needed(self):
		"""Register the case in the standard Logistics Job Number ledger."""
		if self.job_number or not self.company:
			return
		existing = frappe.db.get_value(
			"Job Number",
			{"job_type": self.doctype, "job_no": self.name},
			"name",
		)
		if existing:
			self.db_set("job_number", existing, update_modified=False)
			self.job_number = existing
			return
		try:
			job = frappe.get_doc(
				{
					"doctype": "Job Number",
					"job_type": self.doctype,
					"job_no": self.name,
					"company": self.company,
					"branch": self.branch,
					"cost_center": self.cost_center,
					"profit_center": self.profit_center,
					"job_open_date": now_datetime().date(),
				}
			)
			job.insert(ignore_permissions=True)
			self.db_set("job_number", job.name, update_modified=False)
			self.job_number = job.name
		except Exception:
			frappe.log_error(
				frappe.get_traceback(),
				"Time Sensitive Case Job Number creation failed",
			)

	def _alert_body(self, headline: str) -> str:
		return _(
			"{0}<br>Case: {1}<br>Type: {2}<br>Deadline: {3}<br>SLA: {4}"
		).format(
			headline,
			self.name,
			self.case_type_name or self.case_type,
			self.critical_deadline,
			self.sla_status,
		)


@frappe.whitelist()
def acknowledge_case(name: str):
	doc = frappe.get_doc("Time Sensitive Case", name)
	frappe.has_permission("Time Sensitive Case", "write", doc=doc, throw=True)
	doc.acknowledged_on = now_datetime()
	doc.append_event("Acknowledged", _("Case acknowledged"), severity="informational")
	doc.save()
	return {"name": doc.name, "acknowledged_on": doc.acknowledged_on}


@frappe.whitelist()
def activate_case(name: str):
	doc = frappe.get_doc("Time Sensitive Case", name)
	frappe.has_permission("Time Sensitive Case", "write", doc=doc, throw=True)
	doc.status = "Activated"
	doc.save()
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
def log_case_event(name: str, event_type: str, message: str, severity: str = "informational"):
	doc = frappe.get_doc("Time Sensitive Case", name)
	frappe.has_permission("Time Sensitive Case", "write", doc=doc, throw=True)
	doc.append_event(event_type, message, severity=severity)
	if event_type == "Exception":
		notify_case_event(
			doc,
			event_type="Exception Logged",
			subject=_("Exception on {0}").format(doc.name),
			message=message,
			severity="critical",
		)
	doc.save()
	return {"name": doc.name}


@frappe.whitelist()
def attach_operational_document(case_name: str, doctype: str, docname: str, service_type: str | None = None):
	"""Attach an operational document through a canonical Linked Service."""
	from logistics.time_sensitive.propagation import stamp_document_from_case
	from logistics.time_sensitive.service_linking import (
		create_linked_service_for_case,
		record_operational_usage,
	)
	from logistics.utils.linked_service_usage import get_linked_services_used_by

	case = frappe.get_doc("Time Sensitive Case", case_name)
	frappe.has_permission("Time Sensitive Case", "write", doc=case, throw=True)
	if not frappe.db.exists(doctype, docname):
		frappe.throw(_("{0} {1} not found").format(doctype, docname))
	operational_doc = frappe.get_doc(doctype, docname)
	frappe.has_permission(doctype, "read", doc=operational_doc, throw=True)

	inferred = service_type or _infer_service_type(doctype)
	case_services = set(get_linked_services_used_by(case.doctype, case.name))
	linked_service = None
	for candidate in get_linked_services_used_by(doctype, docname):
		if frappe.db.get_value("Linked Service", candidate, "service_type") == inferred:
			if candidate in case_services:
				frappe.throw(_("{0} {1} is already attached to this case.").format(doctype, docname))
			linked_service = candidate
			break
	if not linked_service:
		linked_service = create_linked_service_for_case(case, inferred).name

	case.append_event(
		"Handoff",
		_("Attached {0} {1}").format(doctype, docname),
		severity="informational",
		linked_doctype=doctype,
		linked_name=docname,
		is_system=1,
	)
	if case.status == "Activated":
		case.status = "In Execution"
	case.save()
	stamp_document_from_case(doctype, docname, case)
	record_operational_usage(case, linked_service, doctype, docname)
	return {
		"name": case.name,
		"linked_service": linked_service,
	}


@frappe.whitelist()
def create_service_document(case_name: str, linked_service: str):
	"""Create the default operational document for a Linked Service."""
	from logistics.time_sensitive.orchestration import create_operational_doc_for_service
	from logistics.time_sensitive.service_linking import get_case_linked_services

	case = frappe.get_doc("Time Sensitive Case", case_name)
	frappe.has_permission("Time Sensitive Case", "write", doc=case, throw=True)
	if linked_service not in {row.name for row in get_case_linked_services(case)}:
		frappe.throw(_("Linked Service {0} is not linked to this case.").format(linked_service))
	created = create_operational_doc_for_service(case, linked_service)
	case.append_event(
		"Handoff",
		_("Created {0} {1}").format(created["doctype"], created["name"]),
		severity="informational",
		linked_doctype=created["doctype"],
		linked_name=created["name"],
		is_system=1,
	)
	if case.status == "Activated":
		case.status = "In Execution"
	case.save()
	return created


def _case_service_choice_row(
	linked,
	*,
	order_no: str,
	job_no: str,
	detail_idx: int | None = None,
) -> dict:
	"""Build one card payload for Create Service dialog."""
	from logistics.time_sensitive.orchestration import SERVICE_TYPE_DEFAULT_DOCTYPE

	service_type = (linked.service_type or "").strip()
	job_type = SERVICE_TYPE_DEFAULT_DOCTYPE.get(service_type, "")
	order_no = (order_no or "").strip()
	job_no = (job_no or "").strip()
	not_creatable_message: str | None = None

	if order_no:
		creatable = False
		badge = order_no
		subtitle = _("Already linked — open the document from Order No above.")
	elif not job_type:
		creatable = False
		badge = _("Pending")
		subtitle = _("No default document for service type {0}.").format(service_type or _("(unknown)"))
		not_creatable_message = subtitle
	elif not frappe.db.exists("DocType", job_type):
		creatable = False
		badge = _("Pending")
		subtitle = _("DocType {0} is not installed.").format(job_type)
		not_creatable_message = subtitle
	elif not frappe.has_permission(job_type, "create"):
		creatable = False
		badge = _("Pending")
		subtitle = _("You do not have permission to create {0}.").format(_(job_type))
		not_creatable_message = subtitle
	else:
		creatable = True
		badge = _("Pending")
		subtitle = _("Creates {0}. Row parameters are applied on create.").format(_(job_type))

	choice: dict = {
		"linked_service": linked.name,
		"service_type": service_type,
		"job_type": job_type,
		"order_no": order_no,
		"job_no": job_no,
		"creatable": creatable,
		"header_title": _(service_type) if service_type else _("(no service type)"),
		"header_badge": badge,
		"header_subtitle": subtitle,
		"internal_job": linked.name,
	}
	if detail_idx is not None:
		choice["detail_idx"] = detail_idx
	if not_creatable_message:
		choice["not_creatable_message"] = not_creatable_message
	return choice


@frappe.whitelist()
def get_case_service_creation_choices(case_name: str):
	"""Build Create Service card options from case Linked Services."""
	from logistics.time_sensitive.service_linking import get_case_linked_services
	from logistics.utils.linked_service_usage import (
		latest_satellite_job_from_usage,
		latest_shipment_from_usage,
	)

	case = frappe.get_doc("Time Sensitive Case", case_name)
	frappe.has_permission("Time Sensitive Case", "read", doc=case, throw=True)

	choices: list[dict] = []
	for idx, linked in enumerate(get_case_linked_services(case), start=1):
		_jt, order_no = latest_satellite_job_from_usage(linked.name)
		_et, job_no = latest_shipment_from_usage(linked.name)
		choices.append(
			_case_service_choice_row(
				linked,
				order_no=order_no or "",
				job_no=job_no or "",
				detail_idx=idx,
			)
		)

	if not choices:
		return {
			"choices": [],
			"blocked_message": _(
				"Add linked services via the Services button before creating a booking / order."
			),
		}
	return {"choices": choices}


@frappe.whitelist()
def get_case_service_creation_preview(case_name: str, linked_service: str):
	"""Preview case fields and charges that will be applied on Create Service."""
	from logistics.time_sensitive.orchestration import (
		SERVICE_TYPE_DEFAULT_DOCTYPE,
		get_charges_for_service,
	)
	from logistics.time_sensitive.service_linking import get_case_linked_services

	case = frappe.get_doc("Time Sensitive Case", case_name)
	frappe.has_permission("Time Sensitive Case", "read", doc=case, throw=True)
	if linked_service not in {row.name for row in get_case_linked_services(case)}:
		frappe.throw(_("Linked Service {0} is not linked to this case.").format(linked_service))

	linked = frappe.get_doc("Linked Service", linked_service)
	service_type = (linked.service_type or "").strip()
	job_type = SERVICE_TYPE_DEFAULT_DOCTYPE.get(service_type, "")

	from logistics.utils.linked_service_usage import latest_satellite_job_from_usage

	_jt, order_no = latest_satellite_job_from_usage(linked.name)
	order_no = (order_no or "").strip()
	creatable = bool(job_type) and not order_no
	not_creatable_message: str | None = None
	if order_no:
		creatable = False
		not_creatable_message = _("Already linked — open the document from Order No above.")
	elif not job_type:
		creatable = False
		not_creatable_message = _("No default document for service type {0}.").format(
			service_type or _("(unknown)")
		)

	charges = get_charges_for_service(case, linked_service, service_type)
	job_detail_parameters = {
		"customer": getattr(case, "customer", None),
		"company": getattr(case, "company", None),
		"origin": getattr(case, "origin", None),
		"destination": getattr(case, "destination", None),
		"critical_deadline": getattr(case, "critical_deadline", None),
		"priority": getattr(case, "priority", None),
		"sales_quote": getattr(case, "sales_quote", None),
	}

	return {
		"job_type": job_type,
		"linked_service": linked_service,
		"service_type": service_type,
		"creatable": creatable,
		"not_creatable_message": not_creatable_message,
		"source_context": {
			"source_doctype": case.doctype,
			"source_name": case.name,
			"customer": getattr(case, "customer", None),
			"company": getattr(case, "company", None),
			"sales_quote": getattr(case, "sales_quote", None),
		},
		"job_detail_parameters": {k: v for k, v in job_detail_parameters.items() if v},
		"charges": charges,
	}


@frappe.whitelist()
def add_linked_service(case_name: str, service_type: str):
	"""Create a canonical Linked Service owned by this case."""
	from logistics.time_sensitive.service_linking import create_linked_service_for_case

	case = frappe.get_doc("Time Sensitive Case", case_name)
	frappe.has_permission("Time Sensitive Case", "write", doc=case, throw=True)
	linked = create_linked_service_for_case(case, service_type)
	case._invalidate_linked_services_view()
	case.append_event(
		"Handoff",
		_("Added linked {0} service {1}").format(linked.service_type, linked.name),
		severity="informational",
		is_system=1,
	)
	case.save()
	return {
		"name": case.name,
		"linked_service": linked.name,
		"service_type": linked.service_type,
	}


@frappe.whitelist()
def list_case_linked_services(case_name: str):
	"""Return Linked Services for the Manage Services dialog."""
	from logistics.time_sensitive.service_linking import get_case_linked_services
	from logistics.utils.linked_service_usage import (
		latest_satellite_job_from_usage,
		latest_shipment_from_usage,
	)

	case = frappe.get_doc("Time Sensitive Case", case_name)
	frappe.has_permission("Time Sensitive Case", "read", doc=case, throw=True)
	rows = []
	for linked in get_case_linked_services(case):
		owned = (
			(linked.parent_booking_type or "") == case.doctype
			and (linked.parent_booking_name or "") == case.name
		)
		job_type, order_no = latest_satellite_job_from_usage(linked.name)
		_et, job_no = latest_shipment_from_usage(linked.name)
		rows.append(
			{
				"linked_service": linked.name,
				"service_type": linked.service_type,
				"owned_by_case": 1 if owned else 0,
				"job_type": job_type or "",
				"order_no": order_no or "",
				"job_no": job_no or "",
			}
		)
	return {"name": case.name, "linked_services": rows}


@frappe.whitelist()
def remove_linked_service(case_name: str, linked_service: str):
	"""Remove a Linked Service from the case (delete if owned, else unlink Usage)."""
	from logistics.time_sensitive.service_linking import get_case_linked_services
	from logistics.utils.linked_service_compat import linked_service_doctype
	from logistics.utils.linked_service_usage import clear_linked_service_usage

	case = frappe.get_doc("Time Sensitive Case", case_name)
	frappe.has_permission("Time Sensitive Case", "write", doc=case, throw=True)
	if not frappe.db.exists("Linked Service", linked_service):
		frappe.throw(_("Linked Service {0} was not found.").format(linked_service))

	linked_names = {row.name for row in get_case_linked_services(case)}
	if linked_service not in linked_names:
		frappe.throw(_("Linked Service {0} is not linked to this case.").format(linked_service))

	if case.status in ("Activated", "In Execution") and len(linked_names) <= 1:
		frappe.throw(
			_("Cannot remove the last Linked Service while the case is {0}.").format(case.status),
			title=_("Linked Service Required"),
		)

	parent_type = frappe.db.get_value("Linked Service", linked_service, "parent_booking_type")
	parent_name = frappe.db.get_value("Linked Service", linked_service, "parent_booking_name")
	owned = parent_type == case.doctype and parent_name == case.name

	if owned:
		frappe.delete_doc(linked_service_doctype(), linked_service, ignore_permissions=True, force=True)
		action = "removed"
		message = _("Removed linked service {0}").format(linked_service)
	else:
		clear_linked_service_usage(case.doctype, case.name, linked_service=linked_service)
		action = "unlinked"
		message = _("Unlinked service {0} from this case").format(linked_service)

	case._invalidate_linked_services_view()
	case.append_event("Handoff", message, severity="informational", is_system=1)
	case.save()
	return {
		"name": case.name,
		"linked_service": linked_service,
		"action": action,
	}


@frappe.whitelist()
def create_change_request_from_case(case_name: str, reason: str | None = None, reuse_draft: int | None = None):
	"""Create a Change Request for this case's completed main-service job."""
	from logistics.time_sensitive.change_request import create_change_request_from_case as _create

	return _create(case_name, reason=reason, reuse_draft=reuse_draft)


@frappe.whitelist()
def create_case_from_sales_quote(sales_quote: str, case_type: str | None = None, critical_deadline: str | None = None):
	"""Create a Time Sensitive Case and reuse the quote's Linked Services."""
	from logistics.time_sensitive.orchestration import build_case_from_sales_quote
	from logistics.time_sensitive.service_linking import (
		create_linked_service_for_case,
		record_case_usage,
	)

	from logistics.time_sensitive.ts_sq_fetch import copy_charges_from_sales_quote_to_case

	sq = frappe.get_doc("Sales Quote", sales_quote)
	frappe.has_permission("Sales Quote", "read", doc=sq, throw=True)
	from logistics.utils.menu_permission import assert_perm

	assert_perm("Time Sensitive Case", "create")
	case = build_case_from_sales_quote(sq, case_type=case_type, critical_deadline=critical_deadline)

	# Seed mappable header gaps + charges (issue #1377) before insert.
	if getattr(sq, "ts_case_type", None) and not case_type:
		case.case_type = sq.ts_case_type
	if not case.cargo_summary:
		case.cargo_summary = (
			getattr(sq, "special_handling_instructions", None)
			or getattr(sq, "description", None)
			or getattr(sq, "scope_title", None)
		)
	if not case.notes:
		case.notes = getattr(sq, "internal_notes", None) or getattr(sq, "external_notes", None)
	copy_charges_from_sales_quote_to_case(case, sq, clear_existing=False)

	case.insert()
	for linked_service in case.flags.get("pending_linked_services") or []:
		record_case_usage(case, linked_service)
	for service_type in case.flags.get("pending_service_types") or []:
		create_linked_service_for_case(case, service_type)
	stamp_sales_quote_from_case(sq.name, case)
	return {"name": case.name}


def stamp_sales_quote_from_case(sales_quote: str, case) -> None:
	"""Bind Sales Quote reverse fields after a case is linked (create-from-quote or GCFQ apply)."""
	if not sales_quote or not case:
		return
	if not frappe.db.exists("Sales Quote", sales_quote):
		return
	if frappe.db.has_column("Sales Quote", "is_time_sensitive"):
		frappe.db.set_value("Sales Quote", sales_quote, "is_time_sensitive", 1, update_modified=False)
	if frappe.db.has_column("Sales Quote", "time_sensitive_case"):
		frappe.db.set_value(
			"Sales Quote", sales_quote, "time_sensitive_case", case.name, update_modified=False
		)
	if frappe.db.has_column("Sales Quote", "critical_deadline") and getattr(case, "critical_deadline", None):
		frappe.db.set_value(
			"Sales Quote",
			sales_quote,
			"critical_deadline",
			case.critical_deadline,
			update_modified=False,
		)


def _infer_service_type(doctype: str) -> str:
	mapping = {
		"Air Booking": "Air",
		"Air Shipment": "Air",
		"Sea Booking": "Sea",
		"Sea Shipment": "Sea",
		"Transport Order": "Transport",
		"Transport Job": "Transport",
		"Declaration Order": "Customs",
		"Declaration": "Customs",
		"VAS Order": "Warehousing",
		"Inbound Order": "Warehousing",
		"Release Order": "Warehousing",
		"Warehouse Job": "Warehousing",
		"Cross-Docking Order": "Cross-Docking",
		"ODDS Order": "On-Demand Last Mile",
	}
	return mapping.get(doctype, "Other")
