# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Create Air / Sea Booking and Transport / Declaration / Inbound Order from Exhibit Internal Job rows.

Mirrors ``logistics.exhibits.doctype.docket.docket_booking_creation`` but for the Exhibit DocType:
each row of ``exhibit.internal_jobs`` (Internal Job Detail) represents one intended main-service job
for the Exhibit, and this module turns those rows into standalone booking/order documents. The new
documents are not internal jobs — they link back to the Exhibit only through the row's ``job_no``
(and through accounting context inherited from the Exhibit / its Project).
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import frappe
from frappe import _
from frappe.utils import today

from logistics.utils.charge_service_type import (
	effective_internal_job_detail_job_type,
	sales_quote_charge_service_types_equal,
)
from logistics.utils.internal_job_from_source import (
	apply_internal_job_detail_row_to_operational_doc,
	coerce_internal_job_detail_idx,
	linked_internal_job_target_is_cancelled,
)


EXHIBIT_CREATABLE_JOB_TYPES: frozenset[str] = frozenset(
	{
		"Air Booking",
		"Sea Booking",
		"Transport Order",
		"Declaration Order",
		"Inbound Order",
	}
)

_TARGET_DOC_LABELS: dict[str, str] = {
	"Air Booking": "Air Booking",
	"Sea Booking": "Sea Booking",
	"Transport Order": "Transport Order",
	"Declaration Order": "Declaration Order",
	"Inbound Order": "Inbound Order",
}


def _dialog_creatable_job_type(row: Any) -> str:
	"""Job type used in Create > Booking/Order. Special Project / Exhibits service rows are not creatable."""
	if not row:
		return ""
	st = (getattr(row, "service_type", None) or "").strip()
	if sales_quote_charge_service_types_equal(st, "Special Project"):
		return ""
	if sales_quote_charge_service_types_equal(st, "Exhibits"):
		return ""
	return effective_internal_job_detail_job_type(row)


_LOGISTICS_EX_CLIENT_ROWS = "_logistics_ex_ij_client_rows"


def _coerce_client_rows(client_value: Any) -> list | None:
	if client_value is None or client_value == "":
		return None
	if isinstance(client_value, str):
		try:
			client_value = frappe.parse_json(client_value)
		except Exception:
			return None
	if not isinstance(client_value, list):
		return None
	return client_value


@contextmanager
def _client_rows_context(client_value: Any):
	key = _LOGISTICS_EX_CLIENT_ROWS
	parsed = _coerce_client_rows(client_value)
	had_before = hasattr(frappe.local, key)
	old_val = getattr(frappe.local, key, None) if had_before else None
	try:
		if parsed is not None:
			setattr(
				frappe.local,
				key,
				[frappe._dict(r) if isinstance(r, dict) else r for r in parsed],
			)
		yield
	finally:
		if parsed is not None:
			if had_before:
				setattr(frappe.local, key, old_val)
			else:
				try:
					delattr(frappe.local, key)
				except AttributeError:
					pass


def _internal_jobs_list(parent_doc: Any) -> list[Any]:
	ov = getattr(frappe.local, _LOGISTICS_EX_CLIENT_ROWS, None)
	if ov is not None:
		return list(ov)
	return list(getattr(parent_doc, "internal_jobs", None) or [])


def _all_rows_for_form(parent_doc: Any, client_rows: Any) -> list[tuple[int, Any]]:
	parsed = _coerce_client_rows(client_rows)
	if parsed is None:
		rows = getattr(parent_doc, "internal_jobs", None) or []
		return [(i, r) for i, r in enumerate(rows, start=1)]
	if (
		not parsed
		and getattr(parent_doc, "name", None)
		and not getattr(parent_doc, "__islocal", False)
	):
		rows = getattr(parent_doc, "internal_jobs", None) or []
		return [(i, r) for i, r in enumerate(rows, start=1)]
	out: list[tuple[int, Any]] = []
	for i, rowd in enumerate(parsed, start=1):
		rw = frappe._dict(rowd) if isinstance(rowd, dict) else rowd
		out.append((i, rw))
	return out


def _resolve_row_for_create(
	parent_doc: Any, job_type: str, idx: int | None
) -> tuple[Any | None, int | None]:
	jt = (job_type or "").strip()
	if idx is not None:
		rows = _internal_jobs_list(parent_doc)
		if idx < 1 or idx > len(rows):
			frappe.throw(_("Invalid Internal Job row."))
		row = rows[idx - 1]
		row_jt = _dialog_creatable_job_type(row)
		if row_jt != jt:
			frappe.throw(_("The selected line is not for {0}.").format(jt))
		jn = (getattr(row, "job_no", None) or "").strip()
		if jn:
			frappe.throw(
				_("This Internal Job line already references {0} {1}.").format(row_jt, jn),
				title=_("Already linked"),
			)
		return row, idx
	rows = _internal_jobs_list(parent_doc)
	for i, r in enumerate(rows, start=1):
		if _dialog_creatable_job_type(r) != jt:
			continue
		if (getattr(r, "job_no", None) or "").strip():
			continue
		return r, i
	return None, None


def _choice_header(job_type: str, row: Any | None, idx: int | None, jn: str) -> dict[str, Any]:
	jt_label = (job_type or "").strip()
	st = (getattr(row, "service_type", None) or "").strip() if row else ""
	title = _(st) if st else (_(jt_label) if jt_label else _("(no service type)"))
	if jn:
		badge = jn
	elif idx is not None:
		badge = _("Pending")
	else:
		badge = _("Job Details")
	if jn:
		subtitle = _("Already linked — open the job from Job No above.")
	elif not st:
		subtitle = _("Select a service type on this line to set the target document type.")
	elif not jt_label:
		# Special Project / Exhibits service rows cannot spawn a booking/order from an Exhibit.
		subtitle = _("This service type cannot be created from an Exhibit.")
	else:
		subtitle = _("Creates {0} linked to this Exhibit.").format(
			_(_TARGET_DOC_LABELS.get(jt_label, jt_label))
		)
	return {"header_title": title, "header_badge": badge, "header_subtitle": subtitle}


@frappe.whitelist()
def get_exhibit_booking_choices(exhibit: str, internal_jobs: Any = None):
	"""Return Create > Booking/Order options for each Internal Job row on an Exhibit."""
	if not exhibit or not frappe.db.exists("Exhibit", exhibit):
		frappe.throw(_("Invalid Exhibit."))
	doc = frappe.get_doc("Exhibit", exhibit)
	doc.check_permission("read")

	choices: list[dict[str, Any]] = []
	for idx, row in _all_rows_for_form(doc, internal_jobs):
		st = (getattr(row, "service_type", None) or "").strip()
		jt = _dialog_creatable_job_type(row)
		jn = (getattr(row, "job_no", None) or "").strip()
		creatable = bool(jt) and jt in EXHIBIT_CREATABLE_JOB_TYPES and not jn
		header = _choice_header(jt, row, idx, jn)
		cancelled = bool(jn and linked_internal_job_target_is_cancelled(jt, jn))
		if cancelled:
			header = {
				**header,
				"header_subtitle": _("Linked to {0} (cancelled).").format(jn),
				"linked_job_cancelled": True,
			}
		choices.append(
			{
				"mode": "detail",
				"detail_idx": idx,
				"job_type": jt,
				"service_type": st or None,
				"job_no": jn or None,
				"creatable": creatable,
				**header,
			}
		)
	return {"choices": choices}


def _resolve_exhibit_org_context(ep_doc: Any) -> dict[str, Any]:
	"""Best-effort accounting context for the new booking/order.

	Exhibit does not store company / branch / cost center / profit center directly,
	so we resolve them from the linked Project (company) and fall back to user/global
	defaults. The rest of the org fields (branch / cost center / profit center) are
	left blank and the user can adjust them on the created document.
	"""
	ctx: dict[str, Any] = {
		"company": None,
		"branch": None,
		"cost_center": None,
		"profit_center": None,
		"project": (getattr(ep_doc, "project", None) or "").strip() or None,
	}

	project = ctx["project"]
	if project and frappe.db.exists("Project", project):
		try:
			project_company = frappe.db.get_value("Project", project, "company")
		except Exception:
			project_company = None
		if project_company:
			ctx["company"] = project_company
			try:
				company_cost_center = frappe.db.get_value("Company", project_company, "cost_center")
				if company_cost_center:
					ctx["cost_center"] = company_cost_center
			except Exception:
				pass

	if not ctx["company"]:
		ctx["company"] = (
			frappe.defaults.get_user_default("Company")
			or frappe.db.get_single_value("Global Defaults", "default_company")
		)

	return ctx


@frappe.whitelist()
def get_exhibit_booking_preview(
	exhibit: str,
	job_type: str,
	internal_job_idx: int | None = None,
	internal_jobs: Any = None,
):
	"""Internal Job row parameters that will inform the new operational document."""
	if not exhibit or not frappe.db.exists("Exhibit", exhibit):
		frappe.throw(_("Invalid Exhibit."))
	doc = frappe.get_doc("Exhibit", exhibit)
	doc.check_permission("read")

	jt = (job_type or "").strip()
	idx = coerce_internal_job_detail_idx(internal_job_idx)
	org = _resolve_exhibit_org_context(doc)

	source_context = {
		"source_doctype": "Exhibit",
		"source_name": doc.name,
		"customer": getattr(doc, "customer", None),
		"company": org.get("company"),
		"project": org.get("project"),
		"sales_quote": None,
		"source_is_internal_job": False,
		"source_main_job_type": None,
		"source_main_job": None,
		"from_main_service_shipment": False,
	}

	with _client_rows_context(internal_jobs):
		rows = _internal_jobs_list(doc)

		if idx is not None and 1 <= idx <= len(rows):
			row_linked = rows[idx - 1]
			jn_linked = (getattr(row_linked, "job_no", None) or "").strip()
			if jn_linked:
				row_jt = _dialog_creatable_job_type(row_linked)
				cancelled = linked_internal_job_target_is_cancelled(row_jt, jn_linked)
				msg = _("This line is already linked to {0}.").format(jn_linked)
				if cancelled:
					msg = _(
						"This line still references {0}, which is cancelled. Reload the Exhibit if the link should have been removed."
					).format(jn_linked)
				return {
					"job_type": jt or row_jt,
					"detail_idx": idx,
					"uses_job_detail_row": True,
					"creatable": False,
					"not_creatable_message": msg,
					"linked_job_cancelled": cancelled,
					"source_context": source_context,
					"target_internal_job": None,
					"job_detail_parameters": {},
					"charges": [],
				}

		if not jt:
			if idx is None:
				frappe.throw(_("Invalid selection."))
			rows[idx - 1]
			return {
				"job_type": "",
				"detail_idx": idx,
				"uses_job_detail_row": True,
				"creatable": False,
				"not_creatable_message": _("Set Service Type on this line before creating."),
				"source_context": source_context,
				"target_internal_job": None,
				"job_detail_parameters": {},
				"charges": [],
			}

		if jt not in EXHIBIT_CREATABLE_JOB_TYPES:
			return {
				"job_type": jt,
				"detail_idx": idx,
				"uses_job_detail_row": True,
				"creatable": False,
				"not_creatable_message": _(
					"This job type cannot be created from an Exhibit. Choose a supported booking/order."
				),
				"source_context": source_context,
				"target_internal_job": None,
				"job_detail_parameters": {},
				"charges": [],
			}

		row, res_idx = _resolve_row_for_create(doc, jt, idx)

		from logistics.utils.sales_quote_charge_parameters import (
			extract_sales_quote_charge_parameters,
		)

		routing_params = extract_sales_quote_charge_parameters(row) if row else {}
		preview_params = {k: v for k, v in (routing_params or {}).items() if k != "charge_group"}

		return {
			"job_type": jt,
			"detail_idx": res_idx,
			"uses_job_detail_row": row is not None,
			"creatable": True,
			"source_context": source_context,
			"target_internal_job": None,
			"job_detail_parameters": preview_params,
			"charges": [],
		}


def _apply_exhibit_context(target_doc: Any, ep_doc: Any) -> None:
	"""Populate accounting and reference fields from the Exhibit onto the new booking/order."""
	meta = frappe.get_meta(target_doc.doctype)
	org = _resolve_exhibit_org_context(ep_doc)

	def _set_if_field(fieldname: str, value: Any) -> None:
		if value in (None, ""):
			return
		if not meta.get_field(fieldname):
			return
		target_doc.set(fieldname, value)

	_set_if_field("company", org.get("company"))
	_set_if_field("branch", org.get("branch"))
	_set_if_field("cost_center", org.get("cost_center"))
	_set_if_field("profit_center", org.get("profit_center"))
	_set_if_field("project", org.get("project"))

	cust = getattr(ep_doc, "customer", None)
	if cust:
		if meta.get_field("local_customer"):
			target_doc.local_customer = cust
		if meta.get_field("customer"):
			target_doc.customer = cust


def _apply_air_sea_corridor_ports_from_row(target_doc: Any, row: Any | None) -> None:
	"""Fill mandatory origin/destination ports from the internal-job row when present."""
	if target_doc.doctype not in ("Air Booking", "Sea Booking"):
		return
	meta = frappe.get_meta(target_doc.doctype)
	if not meta.get_field("origin_port"):
		return
	if not row:
		return

	def _set_if_empty(fieldname: str, value: Any) -> None:
		if value in (None, ""):
			return
		if not meta.get_field(fieldname):
			return
		if not (getattr(target_doc, fieldname, None) or "").strip():
			target_doc.set(fieldname, value)

	for fn in ("origin_port", "destination_port", "direction"):
		_set_if_empty(fn, getattr(row, fn, None))


def _booking_date_field(target_doc: Any) -> str | None:
	meta = frappe.get_meta(target_doc.doctype)
	for fn in ("booking_date", "order_date", "scheduled_date"):
		if meta.get_field(fn):
			return fn
	return None


def _persist_row_link(ep_name: str, job_type: str, job_no: str, detail_idx: int) -> None:
	"""Write job_type and job_no back onto the Exhibit's Internal Job row."""
	if not (job_type and job_no and detail_idx):
		return
	parent = frappe.get_doc("Exhibit", ep_name)
	rows = parent.get("internal_jobs") or []
	if detail_idx < 1 or detail_idx > len(rows):
		frappe.throw(_("Invalid Internal Job row index for persist."))
	row = rows[detail_idx - 1]
	row.job_type = job_type
	row.job_no = job_no
	parent.flags.ignore_validate_update_after_submit = True
	parent.save(ignore_permissions=True)


def _create_air_booking(ep_doc: Any, row: Any, detail_idx: int) -> dict[str, Any]:
	doc = frappe.new_doc("Air Booking")
	_apply_exhibit_context(doc, ep_doc)
	bd = _booking_date_field(doc)
	if bd:
		doc.set(bd, today())
	apply_internal_job_detail_row_to_operational_doc(doc, row, overwrite=True)
	_apply_air_sea_corridor_ports_from_row(doc, row)
	doc.insert(ignore_permissions=True)
	_persist_row_link(ep_doc.name, "Air Booking", doc.name, detail_idx)
	frappe.db.commit()
	return {"air_booking": doc.name, "message": _("Air Booking {0} created.").format(doc.name)}


def _create_sea_booking(ep_doc: Any, row: Any, detail_idx: int) -> dict[str, Any]:
	doc = frappe.new_doc("Sea Booking")
	_apply_exhibit_context(doc, ep_doc)
	bd = _booking_date_field(doc)
	if bd:
		doc.set(bd, today())
	apply_internal_job_detail_row_to_operational_doc(doc, row, overwrite=True)
	_apply_air_sea_corridor_ports_from_row(doc, row)
	doc.insert(ignore_permissions=True)
	_persist_row_link(ep_doc.name, "Sea Booking", doc.name, detail_idx)
	frappe.db.commit()
	return {"sea_booking": doc.name, "message": _("Sea Booking {0} created.").format(doc.name)}


def _create_transport_order(ep_doc: Any, row: Any, detail_idx: int) -> dict[str, Any]:
	from logistics.utils.transport_job_type import (
		apply_container_transport_context_to_order,
		set_internal_transport_order_draft_insert_flags,
	)

	order = frappe.new_doc("Transport Order")
	_apply_exhibit_context(order, ep_doc)
	order.booking_date = today()
	if frappe.get_meta("Transport Order").get_field("transport_job_type"):
		order.transport_job_type = "Non-Container"
	if frappe.get_meta("Transport Order").get_field("scheduled_date"):
		order.scheduled_date = today()
	apply_internal_job_detail_row_to_operational_doc(order, row, overwrite=True)
	apply_container_transport_context_to_order(order, row)
	set_internal_transport_order_draft_insert_flags(order)
	# Exhibit-created orders are standalone, not internal jobs.
	if frappe.get_meta("Transport Order").get_field("is_internal_job"):
		order.is_internal_job = 0
	order.insert(ignore_permissions=True)
	_persist_row_link(ep_doc.name, "Transport Order", order.name, detail_idx)
	frappe.db.commit()
	return {
		"transport_order": order.name,
		"message": _("Transport Order {0} created.").format(order.name),
	}


def _create_declaration_order(ep_doc: Any, row: Any, detail_idx: int) -> dict[str, Any]:
	order = frappe.new_doc("Declaration Order")
	_apply_exhibit_context(order, ep_doc)
	if frappe.get_meta("Declaration Order").get_field("order_date"):
		order.order_date = today()
	if frappe.get_meta("Declaration Order").get_field("transport_mode") and not order.get(
		"transport_mode"
	):
		order.transport_mode = getattr(row, "transport_mode", None) or order.get("transport_mode")
	apply_internal_job_detail_row_to_operational_doc(order, row, overwrite=True)
	if frappe.get_meta("Declaration Order").get_field("is_internal_job"):
		order.is_internal_job = 0
	order.insert(ignore_permissions=True)
	_persist_row_link(ep_doc.name, "Declaration Order", order.name, detail_idx)
	frappe.db.commit()
	return {
		"declaration_order": order.name,
		"message": _("Declaration Order {0} created.").format(order.name),
	}


def _create_inbound_order(ep_doc: Any, row: Any, detail_idx: int) -> dict[str, Any]:
	order = frappe.new_doc("Inbound Order")
	_apply_exhibit_context(order, ep_doc)
	if frappe.get_meta("Inbound Order").get_field("order_date"):
		order.order_date = today()
	apply_internal_job_detail_row_to_operational_doc(order, row, overwrite=True)
	order.insert(ignore_permissions=True)
	_persist_row_link(ep_doc.name, "Inbound Order", order.name, detail_idx)
	frappe.db.commit()
	return {
		"inbound_order": order.name,
		"message": _("Inbound Order {0} created.").format(order.name),
	}


_CREATE_DISPATCH = {
	"Air Booking": _create_air_booking,
	"Sea Booking": _create_sea_booking,
	"Transport Order": _create_transport_order,
	"Declaration Order": _create_declaration_order,
	"Inbound Order": _create_inbound_order,
}


@frappe.whitelist()
def create_booking_or_order_from_exhibit(
	exhibit: str,
	job_type: str,
	internal_job_idx: int | None = None,
	internal_jobs: Any = None,
):
	"""Create the chosen booking/order from the matching Internal Job row on the Exhibit."""
	if not exhibit or not frappe.db.exists("Exhibit", exhibit):
		frappe.throw(_("Invalid Exhibit."))
	jt = (job_type or "").strip()
	if jt not in EXHIBIT_CREATABLE_JOB_TYPES:
		frappe.throw(_("Invalid job type."))

	ep_doc = frappe.get_doc("Exhibit", exhibit)
	ep_doc.check_permission("write")

	idx = coerce_internal_job_detail_idx(internal_job_idx)

	with _client_rows_context(internal_jobs):
		row, resolved_idx = _resolve_row_for_create(ep_doc, jt, idx)
		if row is None:
			frappe.throw(
				_(
					"Add an Internal Job line with service type matching {0}, or select an existing open line."
				).format(jt)
			)
		if resolved_idx is None:
			frappe.throw(_("Could not resolve the Internal Job row to update after creation."))
		handler = _CREATE_DISPATCH[jt]
		return handler(ep_doc, row, resolved_idx)
