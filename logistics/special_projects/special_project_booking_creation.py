# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Create Air/Sea Booking, Transport/Declaration/Inbound Order from Special Project Lifecycle Job rows.

Unlike the operational-job → internal-job flow in ``logistics.utils.internal_job_from_source``, bookings
and orders created from a Special Project are **standalone** (not internal jobs). They link back to the
project via the ``project`` field and reuse the Sales Quote / customer / accounting context from the
Special Project header.

The Lifecycle Job table (``special_project.lifecycle_jobs``) drives this flow: each row represents an
intended main-service job for the project; this module turns those rows into real booking/order
documents and stores the new doc name back on the source row's ``job_no``.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, today

from logistics.special_projects.project_order_copy import (
	build_project_order_from_special_project,
	suggested_order_title_from_lifecycle_row,
)
from logistics.utils.charge_service_type import (
	effective_internal_job_detail_job_type,
	sales_quote_charge_service_types_equal,
)
from logistics.special_projects.special_project_charge_copy import (
	prepare_operational_charges_from_special_project,
)
from logistics.utils.internal_job_from_source import (
	apply_internal_job_detail_row_to_operational_doc,
	coerce_internal_job_detail_idx,
	linked_internal_job_target_is_cancelled,
)


SPECIAL_PROJECT_CREATABLE_JOB_TYPES: frozenset[str] = frozenset(
	{
		"Air Booking",
		"Sea Booking",
		"Transport Order",
		"Declaration Order",
		"Inbound Order",
		"Project Order",
	}
)

# Friendly target labels used for the Create dialog header.
_TARGET_DOC_LABELS: dict[str, str] = {
	"Air Booking": "Air Booking",
	"Sea Booking": "Sea Booking",
	"Transport Order": "Transport Order",
	"Declaration Order": "Declaration Order",
	"Inbound Order": "Inbound Order",
	"Project Order": "Project Order",
}


def _dialog_creatable_job_type(row: Any) -> str:
	"""Job type used in Create > Booking/Order (Special Project service → Project Order, not Project Job)."""
	if not row:
		return ""
	st = (getattr(row, "service_type", None) or "").strip()
	if sales_quote_charge_service_types_equal(st, "Special Project"):
		return "Project Order"
	return effective_internal_job_detail_job_type(row)

_LOGISTICS_SP_CLIENT_ROWS = "_logistics_sp_ij_client_rows"


def _coerce_client_rows(client_value: Any) -> list | None:
	"""List of Internal Job Detail row dicts from the desk form, or None to use the saved document."""
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
	key = _LOGISTICS_SP_CLIENT_ROWS
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


def _lifecycle_rows_list(parent_doc: Any) -> list[Any]:
	ov = getattr(frappe.local, _LOGISTICS_SP_CLIENT_ROWS, None)
	if ov is not None:
		return list(ov)
	return list(getattr(parent_doc, "lifecycle_jobs", None) or [])


def _all_rows_for_form(parent_doc: Any, client_lifecycle_jobs: Any) -> list[tuple[int, Any]]:
	"""All Lifecycle Job rows for the dialog (including those already linked to a Job No)."""
	parsed = _coerce_client_rows(client_lifecycle_jobs)
	if parsed is None:
		rows = getattr(parent_doc, "lifecycle_jobs", None) or []
		return [(i, r) for i, r in enumerate(rows, start=1)]
	if (
		not parsed
		and getattr(parent_doc, "name", None)
		and not getattr(parent_doc, "__islocal", False)
	):
		rows = getattr(parent_doc, "lifecycle_jobs", None) or []
		return [(i, r) for i, r in enumerate(rows, start=1)]
	out: list[tuple[int, Any]] = []
	for i, rowd in enumerate(parsed, start=1):
		rw = frappe._dict(rowd) if isinstance(rowd, dict) else rowd
		out.append((i, rw))
	return out


def _resolve_row_for_create(
	parent_doc: Any, job_type: str, idx: int | None
) -> tuple[Any | None, int | None]:
	"""Resolve the Lifecycle Job row used for create: explicit idx, else first open row for this job_type."""
	jt = (job_type or "").strip()
	if idx is not None:
		rows = _lifecycle_rows_list(parent_doc)
		if idx < 1 or idx > len(rows):
			frappe.throw(_("Invalid Lifecycle Job row."))
		row = rows[idx - 1]
		row_jt = _dialog_creatable_job_type(row)
		if row_jt != jt:
			frappe.throw(_("The selected line is not for {0}.").format(jt))
		jn = (getattr(row, "job_no", None) or "").strip()
		if jn:
			frappe.throw(
				_("This Lifecycle Job line already references {0} {1}.").format(row_jt, jn),
				title=_("Already linked"),
			)
		return row, idx
	rows = _lifecycle_rows_list(parent_doc)
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
		subtitle = _("Could not resolve target document type for this service.")
	else:
		subtitle = _("Creates {0} linked to this Special Project.").format(_(_TARGET_DOC_LABELS.get(jt_label, jt_label)))
	return {"header_title": title, "header_badge": badge, "header_subtitle": subtitle}


@frappe.whitelist()
def get_special_project_booking_choices(
	special_project: str, lifecycle_jobs: Any = None
):
	"""Return Create > Booking/Order options for each Lifecycle Job row on a Special Project."""
	if not special_project or not frappe.db.exists("Special Project", special_project):
		frappe.throw(_("Invalid Special Project."))
	doc = frappe.get_doc("Special Project", special_project)
	doc.check_permission("read")

	choices: list[dict[str, Any]] = []
	for idx, row in _all_rows_for_form(doc, lifecycle_jobs):
		st = (getattr(row, "service_type", None) or "").strip()
		jt = _dialog_creatable_job_type(row)
		jn = (getattr(row, "job_no", None) or "").strip()
		creatable = bool(jt) and jt in SPECIAL_PROJECT_CREATABLE_JOB_TYPES and not jn
		header = _choice_header(jt, row, idx, jn)
		cancelled = bool(
			jn
			and (
				linked_internal_job_target_is_cancelled(jt, jn)
				or (jt == "Project Order" and frappe.db.exists("Project Order", jn) and (frappe.db.get_value("Project Order", jn, "docstatus") or 0) == 2)
			)
		)
		if cancelled:
			header = {
				**header,
				"header_subtitle": _("Linked to {0} (cancelled).").format(jn),
				"linked_job_cancelled": True,
			}
		choice = {
			"mode": "detail",
			"detail_idx": idx,
			"job_type": jt,
			"service_type": st or None,
			"job_no": jn or None,
			"creatable": creatable,
			**header,
		}
		if creatable and jt == "Project Order":
			choice["suggested_order_title"] = suggested_order_title_from_lifecycle_row(doc, row)
		choices.append(choice)
	return {"choices": choices}


@frappe.whitelist()
def get_special_project_booking_preview(
	special_project: str,
	job_type: str,
	lifecycle_job_idx: int | None = None,
	lifecycle_jobs: Any = None,
):
	"""Lifecycle Job parameters and matching charge rows that will inform the new operational document."""
	if not special_project or not frappe.db.exists("Special Project", special_project):
		frappe.throw(_("Invalid Special Project."))
	doc = frappe.get_doc("Special Project", special_project)
	doc.check_permission("read")

	jt = (job_type or "").strip()
	idx = coerce_internal_job_detail_idx(lifecycle_job_idx)

	source_context = {
		"source_doctype": "Special Project",
		"source_name": doc.name,
		"customer": getattr(doc, "customer", None),
		"company": getattr(doc, "company", None),
		"sales_quote": getattr(doc, "sales_quote", None),
		"source_is_internal_job": False,
		"source_main_job_type": None,
		"source_main_job": None,
		"from_main_service_shipment": False,
	}

	with _client_rows_context(lifecycle_jobs):
		rows = _lifecycle_rows_list(doc)

		# Linked-row preview (read-only — already created)
		if idx is not None and 1 <= idx <= len(rows):
			row_linked = rows[idx - 1]
			jn_linked = (getattr(row_linked, "job_no", None) or "").strip()
			if jn_linked:
				row_jt = _dialog_creatable_job_type(row_linked)
				cancelled = linked_internal_job_target_is_cancelled(row_jt, jn_linked)
				if not cancelled and row_jt == "Project Order" and frappe.db.exists("Project Order", jn_linked):
					cancelled = (frappe.db.get_value("Project Order", jn_linked, "docstatus") or 0) == 2
				msg = _("This line is already linked to {0}.").format(jn_linked)
				if cancelled:
					msg = _(
						"This line still references {0}, which is cancelled. Reload the project if the link should have been removed."
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
			row = rows[idx - 1]
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

		if jt not in SPECIAL_PROJECT_CREATABLE_JOB_TYPES:
			return {
				"job_type": jt,
				"detail_idx": idx,
				"uses_job_detail_row": True,
				"creatable": False,
				"not_creatable_message": _(
					"This job type cannot be created from this screen. Choose a supported booking/order."
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

		# Project-level charge preview filtered by service_type when possible.
		charges_preview: list[dict[str, Any]] = []
		from frappe.utils import flt as _flt

		for ch in getattr(doc, "charges", None) or []:
			if jt == "Project Order":
				if not sales_quote_charge_service_types_equal(
					getattr(ch, "service_type", None), "Special Project"
				):
					continue
			else:
				svc_lower = (getattr(row, "service_type", None) or "").strip().lower() if row else ""
				st_ch = (getattr(ch, "service_type", None) or "").strip().lower()
				if svc_lower and st_ch and st_ch != svc_lower:
					continue
			charges_preview.append(
				{
					"service_type": getattr(ch, "service_type", None),
					"item_code": getattr(ch, "item_code", None),
					"item_name": getattr(ch, "item_name", None),
					"rate": _flt(getattr(ch, "rate", None)) or None,
					"unit_rate": _flt(getattr(ch, "unit_rate", None)) or None,
					"per_unit_rate": _flt(getattr(ch, "per_unit_rate", None)) or None,
					"currency": getattr(ch, "currency", None) or getattr(ch, "selling_currency", None),
					"selling_currency": getattr(ch, "selling_currency", None),
					"estimated_revenue": _flt(getattr(ch, "estimated_revenue", None)) or None,
					"parameters": preview_params,
				}
			)

		out = {
			"job_type": jt,
			"detail_idx": res_idx,
			"uses_job_detail_row": row is not None,
			"creatable": True,
			"source_context": source_context,
			"target_internal_job": None,
			"job_detail_parameters": preview_params,
			"charges": charges_preview,
		}
		if jt == "Project Order" and row is not None:
			out["suggested_order_title"] = suggested_order_title_from_lifecycle_row(doc, row)
		return out


def _apply_sales_quote_parties_to_target(target_doc: Any, sp_doc: Any) -> None:
	"""Copy shipper/consignee from the linked Sales Quote (same as quote → booking creation)."""
	sq_name = (getattr(sp_doc, "sales_quote", None) or getattr(target_doc, "sales_quote", None) or "").strip()
	if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
		return
	sq = frappe.get_cached_doc("Sales Quote", sq_name)
	meta = frappe.get_meta(target_doc.doctype)
	for party_fn in ("shipper", "consignee"):
		if not meta.get_field(party_fn):
			continue
		if not (getattr(target_doc, party_fn, None) or "").strip() and getattr(sq, party_fn, None):
			target_doc.set(party_fn, sq.get(party_fn))
	if target_doc.doctype in ("Air Booking", "Sea Booking"):
		from logistics.utils.party_address_contact_from_masters import (
			populate_air_sea_booking_party_fields_from_masters,
		)
		from logistics.utils.shipper_consignee_defaults import apply_shipper_consignee_defaults

		populate_air_sea_booking_party_fields_from_masters(target_doc)
		apply_shipper_consignee_defaults(target_doc)


def _set_main_service_for_one_off_quote_target(target_doc: Any, sp_doc: Any) -> None:
	"""Primary legs from One-off Sales Quotes are main service (Project quotes leave flags unset)."""
	if not hasattr(target_doc, "is_main_service"):
		return
	if cint(getattr(target_doc, "is_internal_job", 0)):
		return
	sq_name = (getattr(sp_doc, "sales_quote", None) or getattr(target_doc, "sales_quote", None) or "").strip()
	if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
		return
	if frappe.db.get_value("Sales Quote", sq_name, "quotation_type") == "One-off":
		target_doc.is_main_service = 1


def _apply_special_project_context(target_doc: Any, sp_doc: Any) -> None:
	"""Populate accounting and reference fields from the Special Project onto the new booking/order."""
	meta = frappe.get_meta(target_doc.doctype)

	def _set_if_field(fieldname: str, value: Any) -> None:
		if value in (None, ""):
			return
		if not meta.get_field(fieldname):
			return
		target_doc.set(fieldname, value)

	_set_if_field("company", getattr(sp_doc, "company", None))
	_set_if_field("branch", getattr(sp_doc, "branch", None))
	_set_if_field("cost_center", getattr(sp_doc, "cost_center", None))
	_set_if_field("profit_center", getattr(sp_doc, "profit_center", None))
	_set_if_field("project", getattr(sp_doc, "project", None) or sp_doc.name)
	_set_if_field("sales_quote", getattr(sp_doc, "sales_quote", None))
	_set_main_service_for_one_off_quote_target(target_doc, sp_doc)
	# Customer fields differ by doctype.
	cust = getattr(sp_doc, "customer", None)
	if cust:
		if meta.get_field("local_customer"):
			target_doc.local_customer = cust
		if meta.get_field("customer"):
			target_doc.customer = cust
	_apply_sales_quote_parties_to_target(target_doc, sp_doc)


def _apply_air_sea_corridor_ports_from_context(
	target_doc: Any, sp_doc: Any, row: Any | None
) -> None:
	"""Fill mandatory origin/destination ports from the lifecycle row or linked Sales Quote."""
	if target_doc.doctype not in ("Air Booking", "Sea Booking"):
		return
	meta = frappe.get_meta(target_doc.doctype)
	if not meta.get_field("origin_port"):
		return

	service = "Air" if target_doc.doctype == "Air Booking" else "Sea"

	def _set_if_empty(fieldname: str, value: Any) -> None:
		if value in (None, ""):
			return
		if not meta.get_field(fieldname):
			return
		if not (getattr(target_doc, fieldname, None) or "").strip():
			target_doc.set(fieldname, value)

	if row:
		for fn in ("origin_port", "destination_port", "direction"):
			_set_if_empty(fn, getattr(row, fn, None))

	if (getattr(target_doc, "origin_port", None) or "").strip() and (
		getattr(target_doc, "destination_port", None) or ""
	).strip():
		return

	sq_name = (
		getattr(sp_doc, "sales_quote", None) or getattr(target_doc, "sales_quote", None) or ""
	).strip()
	if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
		return

	from logistics.pricing_center.doctype.sales_quote.sales_quote import (
		_get_service_params,
		_sq_charge_row_matches_service,
	)

	try:
		sq = frappe.get_doc("Sales Quote", sq_name)
	except Exception:
		return

	first = _get_service_params(sq, service)
	legacy_table = "air_freight" if service == "Air" else "sea_freight"
	legacy_rows = getattr(sq, legacy_table, None) or []
	if not first and legacy_rows:
		first = legacy_rows[0]

	origin = (getattr(target_doc, "origin_port", None) or "").strip() or None
	dest = (getattr(target_doc, "destination_port", None) or "").strip() or None

	if not origin:
		if service == "Air":
			origin = (getattr(first, "origin_port", None) if first else None) or getattr(
				sq, "origin_port", None
			)
		else:
			origin = (
				(getattr(first, "origin_port", None) if first else None)
				or getattr(sq, "origin_port_sea", None)
				or getattr(sq, "origin_port", None)
				or getattr(sq, "location_from", None)
			)
	if not dest:
		if service == "Air":
			dest = (getattr(first, "destination_port", None) if first else None) or getattr(
				sq, "destination_port", None
			)
		else:
			dest = (
				(getattr(first, "destination_port", None) if first else None)
				or getattr(sq, "destination_port_sea", None)
				or getattr(sq, "destination_port", None)
				or getattr(sq, "location_to", None)
			)

	charges = [c for c in (sq.get("charges") or []) if _sq_charge_row_matches_service(c, service)]
	if not origin or not dest:
		for ch in charges:
			if not origin and getattr(ch, "origin_port", None):
				origin = ch.origin_port
			if not dest and getattr(ch, "destination_port", None):
				dest = ch.destination_port
			if origin and dest:
				break

	if (not origin or not dest) and getattr(sq, "routing_legs", None):
		for leg in sq.routing_legs:
			if getattr(leg, "mode", None) != service:
				continue
			if not origin and getattr(leg, "origin", None):
				origin = leg.origin
			if not dest and getattr(leg, "destination", None):
				dest = leg.destination
			if origin and dest:
				break

	_set_if_empty("origin_port", origin)
	_set_if_empty("destination_port", dest)
	if first or getattr(sq, "direction", None):
		_set_if_empty(
			"direction",
			(getattr(first, "direction", None) if first else None) or getattr(sq, "direction", None),
		)


def _prepare_charges_before_insert(sp_doc: Any, target_doc: Any, row: Any | None) -> None:
	"""Copy matching programme charges (or Sales Quote lines) before the first save."""
	prepare_operational_charges_from_special_project(sp_doc, target_doc, row)


def _booking_date_field(target_doc: Any) -> str | None:
	meta = frappe.get_meta(target_doc.doctype)
	for fn in ("booking_date", "order_date", "scheduled_date"):
		if meta.get_field(fn):
			return fn
	return None


def _persist_row_link(sp_name: str, job_type: str, job_no: str, detail_idx: int) -> None:
	"""Write job_type and job_no back onto the Special Project's Lifecycle Job row."""
	if not (job_type and job_no and detail_idx):
		return
	parent = frappe.get_doc("Special Project", sp_name)
	rows = parent.get("lifecycle_jobs") or []
	if detail_idx < 1 or detail_idx > len(rows):
		frappe.throw(_("Invalid Lifecycle Job row index for persist."))
	row = rows[detail_idx - 1]
	row.job_type = job_type
	row.job_no = job_no
	parent.flags.ignore_validate_update_after_submit = True
	parent.flags.ignore_charges_sync = True
	parent.save(ignore_permissions=True)


def _create_air_booking(
	sp_doc: Any, row: Any, detail_idx: int, shipment_lines: Any = None
) -> dict[str, Any]:
	doc = frappe.new_doc("Air Booking")
	_apply_special_project_context(doc, sp_doc)
	bd = _booking_date_field(doc)
	if bd:
		doc.set(bd, today())
	apply_internal_job_detail_row_to_operational_doc(doc, row, overwrite=True)
	_apply_air_sea_corridor_ports_from_context(doc, sp_doc, row)
	_apply_cargo_and_shipment_lines(sp_doc, doc, shipment_lines)
	_prepare_charges_before_insert(sp_doc, doc, row)
	doc.insert(ignore_permissions=True)
	_persist_row_link(sp_doc.name, "Air Booking", doc.name, detail_idx)
	frappe.db.commit()
	return {"air_booking": doc.name, "message": _("Air Booking {0} created.").format(doc.name)}


def _create_sea_booking(
	sp_doc: Any, row: Any, detail_idx: int, shipment_lines: Any = None
) -> dict[str, Any]:
	doc = frappe.new_doc("Sea Booking")
	_apply_special_project_context(doc, sp_doc)
	bd = _booking_date_field(doc)
	if bd:
		doc.set(bd, today())
	apply_internal_job_detail_row_to_operational_doc(doc, row, overwrite=True)
	_apply_air_sea_corridor_ports_from_context(doc, sp_doc, row)
	_apply_cargo_and_shipment_lines(sp_doc, doc, shipment_lines)
	_prepare_charges_before_insert(sp_doc, doc, row)
	doc.insert(ignore_permissions=True)
	_persist_row_link(sp_doc.name, "Sea Booking", doc.name, detail_idx)
	frappe.db.commit()
	return {"sea_booking": doc.name, "message": _("Sea Booking {0} created.").format(doc.name)}


def _create_transport_order(
	sp_doc: Any, row: Any, detail_idx: int, shipment_lines: Any = None
) -> dict[str, Any]:
	from logistics.utils.transport_job_type import (
		apply_container_transport_context_to_order,
		set_internal_transport_order_draft_insert_flags,
	)

	order = frappe.new_doc("Transport Order")
	_apply_special_project_context(order, sp_doc)
	order.booking_date = today()
	if frappe.get_meta("Transport Order").get_field("transport_job_type"):
		order.transport_job_type = "Non-Container"
	if frappe.get_meta("Transport Order").get_field("scheduled_date"):
		order.scheduled_date = today()
	apply_internal_job_detail_row_to_operational_doc(order, row, overwrite=True)
	apply_container_transport_context_to_order(order, row)
	set_internal_transport_order_draft_insert_flags(order)
	# Special Project orders are standalone, not internal jobs.
	if frappe.get_meta("Transport Order").get_field("is_internal_job"):
		order.is_internal_job = 0
	_apply_cargo_and_shipment_lines(sp_doc, order, shipment_lines)
	_prepare_charges_before_insert(sp_doc, order, row)
	order.insert(ignore_permissions=True)
	_persist_row_link(sp_doc.name, "Transport Order", order.name, detail_idx)
	frappe.db.commit()
	return {"transport_order": order.name, "message": _("Transport Order {0} created.").format(order.name)}


def _create_declaration_order(
	sp_doc: Any, row: Any, detail_idx: int, shipment_lines: Any = None
) -> dict[str, Any]:
	order = frappe.new_doc("Declaration Order")
	_apply_special_project_context(order, sp_doc)
	if frappe.get_meta("Declaration Order").get_field("order_date"):
		order.order_date = today()
	if frappe.get_meta("Declaration Order").get_field("transport_mode") and not order.get("transport_mode"):
		order.transport_mode = getattr(row, "transport_mode", None) or order.get("transport_mode")
	apply_internal_job_detail_row_to_operational_doc(order, row, overwrite=True)
	if frappe.get_meta("Declaration Order").get_field("is_internal_job"):
		order.is_internal_job = 0
	_prepare_charges_before_insert(sp_doc, order, row)
	order.insert(ignore_permissions=True)
	_persist_row_link(sp_doc.name, "Declaration Order", order.name, detail_idx)
	frappe.db.commit()
	return {
		"declaration_order": order.name,
		"message": _("Declaration Order {0} created.").format(order.name),
	}


def _create_inbound_order(
	sp_doc: Any, row: Any, detail_idx: int, shipment_lines: Any = None
) -> dict[str, Any]:
	order = frappe.new_doc("Inbound Order")
	_apply_special_project_context(order, sp_doc)
	if frappe.get_meta("Inbound Order").get_field("order_date"):
		order.order_date = today()
	apply_internal_job_detail_row_to_operational_doc(order, row, overwrite=True)
	_apply_cargo_and_shipment_lines(sp_doc, order, shipment_lines)
	_prepare_charges_before_insert(sp_doc, order, row)
	order.insert(ignore_permissions=True)
	_persist_row_link(sp_doc.name, "Inbound Order", order.name, detail_idx)
	frappe.db.commit()
	return {"inbound_order": order.name, "message": _("Inbound Order {0} created.").format(order.name)}


def _create_project_order(
	sp_doc: Any, row: Any, detail_idx: int, order_title: str | None = None
) -> dict[str, Any]:
	title = (order_title or "").strip()
	if not title:
		frappe.throw(_("Order Title is required to create a Project Order."))
	order = build_project_order_from_special_project(sp_doc, title, lifecycle_row=row)
	order.insert(ignore_permissions=True)
	_persist_row_link(sp_doc.name, "Project Order", order.name, detail_idx)
	frappe.db.commit()
	return {
		"project_order": order.name,
		"message": _("Project Order {0} created.").format(order.name),
	}


_CREATE_DISPATCH = {
	"Air Booking": _create_air_booking,
	"Sea Booking": _create_sea_booking,
	"Transport Order": _create_transport_order,
	"Declaration Order": _create_declaration_order,
	"Inbound Order": _create_inbound_order,
	"Project Order": _create_project_order,
}


def _apply_cargo_and_shipment_lines(
	sp_doc: Any, target_doc: Any, shipment_lines: Any = None
) -> None:
	from logistics.special_projects.special_project_packages import (
		apply_shipment_lines_to_target,
		copy_always_along_packages_to_target,
	)

	if shipment_lines:
		apply_shipment_lines_to_target(sp_doc, target_doc, shipment_lines)
	if target_doc.doctype in ("Air Booking", "Sea Booking", "Transport Order", "Inbound Order"):
		copy_always_along_packages_to_target(sp_doc, target_doc)


@frappe.whitelist()
def create_booking_or_order_from_special_project(
	special_project: str,
	job_type: str,
	lifecycle_job_idx: int | None = None,
	lifecycle_jobs: Any = None,
	order_title: str | None = None,
	shipment_lines: Any = None,
):
	"""Create the chosen booking/order from the matching Lifecycle Job row on the Special Project."""
	if not special_project or not frappe.db.exists("Special Project", special_project):
		frappe.throw(_("Invalid Special Project."))
	jt = (job_type or "").strip()
	if jt not in SPECIAL_PROJECT_CREATABLE_JOB_TYPES:
		frappe.throw(_("Invalid job type."))

	sp_doc = frappe.get_doc("Special Project", special_project)
	sp_doc.check_permission("write")

	idx = coerce_internal_job_detail_idx(lifecycle_job_idx)

	with _client_rows_context(lifecycle_jobs):
		row, resolved_idx = _resolve_row_for_create(sp_doc, jt, idx)
		if row is None:
			frappe.throw(
				_(
					"Add a Lifecycle Job line with service type matching {0}, or select an existing open line."
				).format(jt)
			)
		if resolved_idx is None:
			frappe.throw(_("Could not resolve the Lifecycle Job row to update after creation."))
		handler = _CREATE_DISPATCH[jt]
		if jt == "Project Order":
			return handler(sp_doc, row, resolved_idx, order_title=order_title)
		return handler(sp_doc, row, resolved_idx, shipment_lines=shipment_lines)
