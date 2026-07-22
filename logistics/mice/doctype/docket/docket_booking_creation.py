# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Create Air / Sea Booking and Transport / Declaration / Inbound Order from Docket Internal Job rows.

Mirrors ``logistics.special_projects.special_project_booking_creation`` but for the Docket DocType:
each row of ``docket.internal_jobs`` (Internal Job Detail) represents one intended main-service job
for the docket, and this module turns those rows into standalone booking/order documents. The new
documents are not internal jobs — they link back to the Docket only through the row's ``job_no``
(and through accounting context / linked Sales Quote).
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import frappe
from frappe import _
from frappe.utils import flt, today

from logistics.utils.charge_service_type import (
	effective_internal_job_detail_job_type,
	sales_quote_charge_service_types_equal,
)
from logistics.utils.internal_job_from_source import (
	apply_internal_job_detail_row_to_operational_doc,
	coerce_internal_job_detail_idx,
	linked_internal_job_target_is_cancelled,
)
from logistics.utils.linked_service_compat import linked_service_rows


DOCKET_CREATABLE_JOB_TYPES: frozenset[str] = frozenset(
	{
		"Air Booking",
		"Sea Booking",
		"Transport Order",
		"Declaration Order",
		"Inbound Order",
		"Cross-Docking Order",
		"MICE Order",
	}
)

_TARGET_DOC_LABELS: dict[str, str] = {
	"Air Booking": "Air Booking",
	"Sea Booking": "Sea Booking",
	"Transport Order": "Transport Order",
	"Declaration Order": "Declaration Order",
	"Inbound Order": "Inbound Order",
	"Cross-Docking Order": "Cross-Docking Order",
	"MICE Order": "MICE Order",
}


def _dialog_creatable_job_type(row: Any) -> str:
	"""Job type used in Create > Booking/Order. Special Project service → Project Order; MICE → MICE Order."""
	if not row:
		return ""
	st = (getattr(row, "service_type", None) or "").strip()
	if sales_quote_charge_service_types_equal(st, "Special Project"):
		return ""
	if sales_quote_charge_service_types_equal(st, "MICE"):
		return "MICE Order"
	return effective_internal_job_detail_job_type(row)


_LOGISTICS_DK_CLIENT_ROWS = "_logistics_dk_ij_client_rows"


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
	key = _LOGISTICS_DK_CLIENT_ROWS
	parsed = _coerce_client_rows(client_value)
	# Empty list is not a useful override — virtual Linked Services grids often serialize as [].
	install = parsed is not None and len(parsed) > 0
	had_before = hasattr(frappe.local, key)
	old_val = getattr(frappe.local, key, None) if had_before else None
	try:
		if install:
			setattr(
				frappe.local,
				key,
				[frappe._dict(r) if isinstance(r, dict) else r for r in parsed],
			)
		yield
	finally:
		if install:
			if had_before:
				setattr(frappe.local, key, old_val)
			else:
				try:
					delattr(frappe.local, key)
				except AttributeError:
					pass


def _resolve_client_rows(client_value: Any, linked_services: Any = None) -> Any:
	"""Accept desk payload from ``linked_services`` or legacy ``internal_jobs``."""
	if client_value is not None and client_value != "":
		return client_value
	return linked_services


def _linked_services_list(parent_doc: Any) -> list[Any]:
	ov = getattr(frappe.local, _LOGISTICS_DK_CLIENT_ROWS, None)
	if ov:
		return list(ov)
	return linked_service_rows(parent_doc)


def _all_rows_for_form(parent_doc: Any, client_rows: Any, linked_services: Any = None) -> list[tuple[int, Any]]:
	client_rows = _resolve_client_rows(client_rows, linked_services)
	parsed = _coerce_client_rows(client_rows)
	if parsed is None:
		rows = linked_service_rows(parent_doc)
		return [(i, r) for i, r in enumerate(rows, start=1)]
	if (
		not parsed
		and getattr(parent_doc, "name", None)
		and not getattr(parent_doc, "__islocal", False)
	):
		rows = linked_service_rows(parent_doc)
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
		rows = _linked_services_list(parent_doc)
		if idx < 1 or idx > len(rows):
			frappe.throw(_("Invalid Linked Service row."))
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
	rows = _linked_services_list(parent_doc)
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
		# Special Project / Exhibits service rows cannot spawn a booking/order from a Docket.
		subtitle = _("This service type cannot be created from a Docket.")
	else:
		subtitle = _("Creates {0} linked to this Docket.").format(
			_(_TARGET_DOC_LABELS.get(jt_label, jt_label))
		)
	return {"header_title": title, "header_badge": badge, "header_subtitle": subtitle}


@frappe.whitelist()
def get_docket_booking_choices(docket: str, internal_jobs: Any = None, linked_services: Any = None):
	"""Return Create > Booking/Order options for each Linked Service row on a Docket."""
	if not docket or not frappe.db.exists("Docket", docket):
		frappe.throw(_("Invalid Docket."))
	doc = frappe.get_doc("Docket", docket)
	doc.check_permission("read")

	client_rows = _resolve_client_rows(internal_jobs, linked_services)
	with _client_rows_context(client_rows):
		from logistics.utils.internal_job_persistence import (
			ensure_linked_service_rows_materialized,
		)

		# Heal missing SQ→Docket clones so the dialog is not empty when the virtual grid is.
		ensure_linked_service_rows_materialized(doc)
		choices: list[dict[str, Any]] = []
		for idx, row in _all_rows_for_form(doc, client_rows):
			st = (getattr(row, "service_type", None) or "").strip()
			jt = _dialog_creatable_job_type(row)
			jn = (getattr(row, "job_no", None) or "").strip()
			creatable = bool(jt) and jt in DOCKET_CREATABLE_JOB_TYPES and not jn
			not_creatable_message = None
			if creatable:
				from logistics.utils.internal_job_creation_eligibility import (
					evaluate_internal_job_creation_eligibility,
				)

				elig = evaluate_internal_job_creation_eligibility(
					sales_quote=getattr(doc, "sales_quote", None),
					parent_doc=doc,
					ij_row=row,
					service_type_label=st,
				)
				if not elig.get("eligible"):
					creatable = False
					not_creatable_message = elig.get("message")
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
					"not_creatable_message": not_creatable_message,
					**header,
				}
			)
	return {"choices": choices}


@frappe.whitelist()
def get_docket_booking_preview(
	docket: str,
	job_type: str,
	internal_job_idx: int | None = None,
	internal_jobs: Any = None,
	linked_services: Any = None,
):
	"""Internal Job row parameters and matching charge rows that will inform the new operational document."""
	if not docket or not frappe.db.exists("Docket", docket):
		frappe.throw(_("Invalid Docket."))
	doc = frappe.get_doc("Docket", docket)
	doc.check_permission("read")

	jt = (job_type or "").strip()
	idx = coerce_internal_job_detail_idx(internal_job_idx)

	source_context = {
		"source_doctype": "Docket",
		"source_name": doc.name,
		"customer": getattr(doc, "exhibitor", None) or getattr(doc, "customer", None),
		"company": getattr(doc, "company", None),
		"sales_quote": getattr(doc, "sales_quote", None),
		"source_is_internal_job": False,
		"source_main_job_type": None,
		"source_main_job": None,
		"from_main_service_shipment": False,
	}

	client_rows = _resolve_client_rows(internal_jobs, linked_services)
	with _client_rows_context(client_rows):
		from logistics.utils.internal_job_persistence import (
			ensure_linked_service_rows_materialized,
		)

		ensure_linked_service_rows_materialized(doc)
		rows = _linked_services_list(doc)

		if idx is not None and 1 <= idx <= len(rows):
			row_linked = rows[idx - 1]
			jn_linked = (getattr(row_linked, "job_no", None) or "").strip()
			if jn_linked:
				row_jt = _dialog_creatable_job_type(row_linked)
				cancelled = linked_internal_job_target_is_cancelled(row_jt, jn_linked)
				msg = _("This line is already linked to {0}.").format(jn_linked)
				if cancelled:
					msg = _(
						"This line still references {0}, which is cancelled. Reload the docket if the link should have been removed."
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

		if jt not in DOCKET_CREATABLE_JOB_TYPES:
			return {
				"job_type": jt,
				"detail_idx": idx,
				"uses_job_detail_row": True,
				"creatable": False,
				"not_creatable_message": _(
					"This job type cannot be created from a Docket. Choose a supported booking/order."
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

		from frappe.utils import flt as _flt

		charges_preview: list[dict[str, Any]] = []
		row_st_lower = (getattr(row, "service_type", None) or "").strip().lower() if row else ""
		for ch in getattr(doc, "charges", None) or []:
			ch_st_lower = (getattr(ch, "service_type", None) or "").strip().lower()
			if row_st_lower and ch_st_lower and ch_st_lower != row_st_lower:
				continue
			charges_preview.append(
				{
					"service_type": getattr(ch, "service_type", None),
					"item_code": getattr(ch, "item_code", None),
					"item_name": getattr(ch, "item_name", None),
					"unit_rate": _flt(getattr(ch, "unit_rate", None)) or None,
					"per_unit_rate": _flt(getattr(ch, "per_unit_rate", None)) or None,
					"currency": getattr(ch, "currency", None) or getattr(ch, "selling_currency", None),
					"selling_currency": getattr(ch, "selling_currency", None),
					"estimated_revenue": _flt(getattr(ch, "estimated_revenue", None)) or None,
					"parameters": preview_params,
				}
			)

		from logistics.utils.internal_job_creation_eligibility import (
			apply_eligibility_to_preview_flags,
		)

		return apply_eligibility_to_preview_flags(
			{
				"job_type": jt,
				"detail_idx": res_idx,
				"uses_job_detail_row": row is not None,
				"creatable": True,
				"source_context": source_context,
				"target_internal_job": None,
				"job_detail_parameters": preview_params,
				"charges": charges_preview,
			},
			sales_quote=getattr(doc, "sales_quote", None),
			parent_doc=doc,
			ij_row=row,
			service_type_label=(getattr(row, "service_type", None) or "").strip() if row else None,
		)


def _apply_sales_quote_parties_to_target(target_doc: Any, dk_doc: Any) -> None:
	"""Copy shipper/consignee from the linked Sales Quote (same as quote → booking creation)."""
	sq_name = (
		getattr(dk_doc, "sales_quote", None) or getattr(target_doc, "sales_quote", None) or ""
	).strip()
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


def _resolve_project_for_target(dk_doc: Any) -> str | None:
	"""Pull a Project link from the Docket's parent Exhibit (Docket itself has no project field)."""
	exhibit_name = (getattr(dk_doc, "exhibit", None) or "").strip()
	if not exhibit_name:
		return None
	try:
		project = frappe.db.get_value("MICE Project", exhibit_name, "project")
	except Exception:
		return None
	return (project or "").strip() or None


def _apply_docket_context(target_doc: Any, dk_doc: Any) -> None:
	"""Populate accounting and reference fields from the Docket onto the new booking/order."""
	meta = frappe.get_meta(target_doc.doctype)

	def _set_if_field(fieldname: str, value: Any) -> None:
		if value in (None, ""):
			return
		if not meta.get_field(fieldname):
			return
		target_doc.set(fieldname, value)

	_set_if_field("company", getattr(dk_doc, "company", None))
	_set_if_field("branch", getattr(dk_doc, "branch", None))
	_set_if_field("cost_center", getattr(dk_doc, "cost_center", None))
	_set_if_field("profit_center", getattr(dk_doc, "profit_center", None))
	_set_if_field("project", _resolve_project_for_target(dk_doc))
	_set_if_field("sales_quote", getattr(dk_doc, "sales_quote", None))

	cust = getattr(dk_doc, "exhibitor", None) or getattr(dk_doc, "customer", None)
	if cust:
		if meta.get_field("local_customer"):
			target_doc.local_customer = cust
		if meta.get_field("customer"):
			target_doc.customer = cust
	_apply_sales_quote_parties_to_target(target_doc, dk_doc)


def _apply_air_sea_corridor_ports_from_context(
	target_doc: Any, dk_doc: Any, row: Any | None
) -> None:
	"""Fill mandatory origin/destination ports from the internal-job row or linked Sales Quote."""
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
		getattr(dk_doc, "sales_quote", None) or getattr(target_doc, "sales_quote", None) or ""
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


def _prepare_charges_before_insert(dk_doc: Any, target_doc: Any, row: Any | None) -> None:
	"""Copy Docket charges (filtered by service_type) onto the new operational doc before insert.

	Charges copied from the Docket are tagged ``charge_scope = "Linked"`` with ``internal_job``
	set to the IJ link stamped on the source ``internal_jobs`` row. The Docket's own ``charges`` table
	can hold both Main- and linked-scoped rows; the spawned booking represents one specific Internal Job
	on the Docket, so every row landing on it carries that linked scope/link.
	"""
	from logistics.utils.charge_service_type import (
		canonical_charge_service_type_for_storage,
		implied_service_type_for_doctype,
		operational_booking_charge_service_type_label,
	)
	from logistics.utils.internal_job_charge_copy import _scrub_main_row_to_child_dict
	from logistics.utils.linked_service_compat import normalize_charge_scope
	from logistics.utils.sales_quote_charge_copy import (
		SCOPE_INTERNAL_JOB,
		stamp_scope_fields_on_charge_row,
	)

	target_meta = frappe.get_meta(target_doc.doctype)
	charges_df = target_meta.get_field("charges")
	if not charges_df or charges_df.fieldtype != "Table":
		return
	target_child_dt = (charges_df.options or "").strip()
	if not target_child_dt:
		return

	row_st = (getattr(row, "service_type", None) or "").strip() if row else ""
	row_ij = (
		(getattr(row, "internal_job", None) or getattr(row, "linked_service", None) or "").strip()
		if row
		else ""
	)
	implied = implied_service_type_for_doctype(target_doc.doctype)
	forced_label = operational_booking_charge_service_type_label(
		row_st or implied, default=row_st or "Transport"
	)
	parent_implied_canonical = canonical_charge_service_type_for_storage(implied)
	if (
		canonical_charge_service_type_for_storage(forced_label) in ("special project", "exhibits")
		and parent_implied_canonical not in ("special project", "exhibits")
	):
		forced_label = operational_booking_charge_service_type_label(implied, default="Transport")

	row_st_lower = row_st.lower()
	new_rows: list[dict[str, Any]] = []
	for ch in getattr(dk_doc, "charges", None) or []:
		ch_st_lower = (getattr(ch, "service_type", None) or "").strip().lower()
		if row_st_lower and ch_st_lower and ch_st_lower != row_st_lower:
			continue
		scrubbed = _scrub_main_row_to_child_dict(ch, target_child_dt, forced_label)
		if scrubbed:
			if scrubbed.get("charge_scope"):
				scrubbed["charge_scope"] = normalize_charge_scope(scrubbed["charge_scope"])
			stamp_scope_fields_on_charge_row(scrubbed, SCOPE_INTERNAL_JOB, row_ij or None)
			new_rows.append(scrubbed)

	if not new_rows:
		_populate_charges_from_linked_sales_quote(target_doc)
		from logistics.utils.charge_service_type import filter_operational_doc_charges_for_internal_job_row

		filter_operational_doc_charges_for_internal_job_row(target_doc, row)
		if row_ij:
			for r in getattr(target_doc, "charges", None) or []:
				stamp_scope_fields_on_charge_row(r, SCOPE_INTERNAL_JOB, row_ij)
		return

	target_doc.set("charges", [])
	for r in new_rows:
		target_doc.append("charges", r)


def _populate_charges_from_linked_sales_quote(target_doc: Any) -> None:
	"""Fallback charge population from Sales Quote when the Docket has no matching rows."""
	sq_name = getattr(target_doc, "sales_quote", None)
	if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
		return

	dt = target_doc.doctype
	try:
		if dt == "Air Booking":
			from logistics.utils.internal_job_from_source import (
				_populate_air_booking_charges_from_linked_quote_on_internal_create,
			)

			_populate_air_booking_charges_from_linked_quote_on_internal_create(target_doc)
		elif dt == "Sea Booking":
			from logistics.utils.internal_job_from_source import (
				_populate_sea_booking_charges_from_linked_quote_on_internal_create,
			)

			_populate_sea_booking_charges_from_linked_quote_on_internal_create(target_doc)
		elif dt == "Transport Order" and hasattr(target_doc, "_populate_charges_from_sales_quote"):
			target_doc._populate_charges_from_sales_quote()
		elif dt == "Declaration Order" and hasattr(target_doc, "_populate_charges_from_sales_quote"):
			target_doc._populate_charges_from_sales_quote()
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			f"Docket — Sales Quote charge population on {dt} create",
		)


def _booking_date_field(target_doc: Any) -> str | None:
	meta = frappe.get_meta(target_doc.doctype)
	for fn in ("booking_date", "order_date", "scheduled_date"):
		if meta.get_field(fn):
			return fn
	return None


def _persist_row_link(dk_name: str, job_type: str, job_no: str, detail_idx: int) -> None:
	"""Write job_type and job_no back onto the Docket's Internal Job row."""
	from logistics.utils.internal_job_detail_copy import persist_internal_job_detail_job_link

	persist_internal_job_detail_job_link(
		"Docket", dk_name, job_type, job_no, detail_idx=detail_idx
	)


def _refresh_target_packing_totals(target_doc: Any) -> None:
	if hasattr(target_doc, "_prepare_header_totals_for_charge_calculation"):
		target_doc._prepare_header_totals_for_charge_calculation()
	elif hasattr(target_doc, "_update_packing_summary"):
		target_doc._update_packing_summary()


def _copy_docket_packages_to_target(dk_doc: Any, target_doc: Any) -> None:
	"""Copy Docket package lines onto a newly created booking/order where supported."""
	packages = getattr(dk_doc, "packages", None) or []
	if not packages:
		return

	from logistics.utils.internal_job_from_source import (
		_SKIP_PACKAGE_ROW_SYSTEM_FIELDS,
		_SKIP_PACKAGE_TABLE_LAYOUT_TYPES,
		_child_doctype_for_table_field,
		_copy_table_rows_matching_target_child_fields,
	)

	target_meta = frappe.get_meta(target_doc.doctype)
	packages_df = target_meta.get_field("packages")
	items_df = target_meta.get_field("items")

	if packages_df and packages_df.fieldtype == "Float":
		if hasattr(dk_doc, "_update_packing_summary"):
			dk_doc._update_packing_summary()
		target_doc.packages = flt(getattr(dk_doc, "total_packages", 0))
		return

	if packages_df and packages_df.fieldtype == "Table":
		child_dt = _child_doctype_for_table_field(target_doc.doctype, "packages")
		if child_dt:
			_copy_table_rows_matching_target_child_fields(
				packages,
				target_doc,
				table_fieldname="packages",
				target_child_doctype=child_dt,
			)
			_refresh_target_packing_totals(target_doc)
		return

	if items_df and items_df.fieldtype == "Table":
		child_dt = _child_doctype_for_table_field(target_doc.doctype, "items")
		if not child_dt:
			return
		tgt_child_meta = frappe.get_meta(child_dt)
		allowed = {
			f.fieldname
			for f in tgt_child_meta.fields
			if f.fieldtype not in _SKIP_PACKAGE_TABLE_LAYOUT_TYPES
		} - _SKIP_PACKAGE_ROW_SYSTEM_FIELDS
		for src_row in packages:
			row_dict: dict[str, Any] = {}
			for fn in allowed:
				if fn == "item":
					wh = getattr(src_row, "warehouse_item", None)
					if wh:
						row_dict["item"] = wh
					continue
				if hasattr(src_row, fn):
					row_dict[fn] = getattr(src_row, fn, None)
			if not row_dict:
				continue
			if all(v is None or v == "" for v in row_dict.values()):
				continue
			target_doc.append("items", row_dict)


def _create_air_booking(dk_doc: Any, row: Any, detail_idx: int) -> dict[str, Any]:
	doc = frappe.new_doc("Air Booking")
	_apply_docket_context(doc, dk_doc)
	bd = _booking_date_field(doc)
	if bd:
		doc.set(bd, today())
	apply_internal_job_detail_row_to_operational_doc(doc, row, overwrite=True)
	_apply_air_sea_corridor_ports_from_context(doc, dk_doc, row)
	_copy_docket_packages_to_target(dk_doc, doc)
	_prepare_charges_before_insert(dk_doc, doc, row)
	doc.insert(ignore_permissions=True)
	_persist_row_link(dk_doc.name, "Air Booking", doc.name, detail_idx)
	frappe.db.commit()
	return {"air_booking": doc.name, "message": _("Air Booking {0} created.").format(doc.name)}


def _create_sea_booking(dk_doc: Any, row: Any, detail_idx: int) -> dict[str, Any]:
	doc = frappe.new_doc("Sea Booking")
	_apply_docket_context(doc, dk_doc)
	bd = _booking_date_field(doc)
	if bd:
		doc.set(bd, today())
	apply_internal_job_detail_row_to_operational_doc(doc, row, overwrite=True)
	_apply_air_sea_corridor_ports_from_context(doc, dk_doc, row)
	_copy_docket_packages_to_target(dk_doc, doc)
	_prepare_charges_before_insert(dk_doc, doc, row)
	doc.insert(ignore_permissions=True)
	_persist_row_link(dk_doc.name, "Sea Booking", doc.name, detail_idx)
	frappe.db.commit()
	return {"sea_booking": doc.name, "message": _("Sea Booking {0} created.").format(doc.name)}


def _create_transport_order(dk_doc: Any, row: Any, detail_idx: int) -> dict[str, Any]:
	from logistics.utils.transport_job_type import (
		apply_container_transport_context_to_order,
		set_internal_transport_order_draft_insert_flags,
	)

	order = frappe.new_doc("Transport Order")
	_apply_docket_context(order, dk_doc)
	order.booking_date = today()
	if frappe.get_meta("Transport Order").get_field("transport_job_type"):
		order.transport_job_type = "Non-Container"
	if frappe.get_meta("Transport Order").get_field("scheduled_date"):
		order.scheduled_date = today()
	apply_internal_job_detail_row_to_operational_doc(order, row, overwrite=True)
	apply_container_transport_context_to_order(order, row)
	set_internal_transport_order_draft_insert_flags(order)
	# Docket-created orders are standalone, not linked satellites.
	from logistics.utils.service_role_rules import apply_standalone_service_flags

	apply_standalone_service_flags(order)
	_copy_docket_packages_to_target(dk_doc, order)
	_prepare_charges_before_insert(dk_doc, order, row)
	order.insert(ignore_permissions=True)
	_persist_row_link(dk_doc.name, "Transport Order", order.name, detail_idx)
	frappe.db.commit()
	return {
		"transport_order": order.name,
		"message": _("Transport Order {0} created.").format(order.name),
	}


def _create_declaration_order(dk_doc: Any, row: Any, detail_idx: int) -> dict[str, Any]:
	order = frappe.new_doc("Declaration Order")
	_apply_docket_context(order, dk_doc)
	if frappe.get_meta("Declaration Order").get_field("order_date"):
		order.order_date = today()
	if frappe.get_meta("Declaration Order").get_field("transport_mode") and not order.get(
		"transport_mode"
	):
		order.transport_mode = getattr(row, "transport_mode", None) or order.get("transport_mode")
	apply_internal_job_detail_row_to_operational_doc(order, row, overwrite=True)
	from logistics.utils.service_role_rules import apply_standalone_service_flags

	apply_standalone_service_flags(order)
	_copy_docket_packages_to_target(dk_doc, order)
	_prepare_charges_before_insert(dk_doc, order, row)
	order.insert(ignore_permissions=True)
	_persist_row_link(dk_doc.name, "Declaration Order", order.name, detail_idx)
	frappe.db.commit()
	return {
		"declaration_order": order.name,
		"message": _("Declaration Order {0} created.").format(order.name),
	}


def _create_inbound_order(dk_doc: Any, row: Any, detail_idx: int) -> dict[str, Any]:
	order = frappe.new_doc("Inbound Order")
	_apply_docket_context(order, dk_doc)
	if frappe.get_meta("Inbound Order").get_field("order_date"):
		order.order_date = today()
	apply_internal_job_detail_row_to_operational_doc(order, row, overwrite=True)
	_copy_docket_packages_to_target(dk_doc, order)
	_prepare_charges_before_insert(dk_doc, order, row)
	order.insert(ignore_permissions=True)
	_persist_row_link(dk_doc.name, "Inbound Order", order.name, detail_idx)
	frappe.db.commit()
	return {
		"inbound_order": order.name,
		"message": _("Inbound Order {0} created.").format(order.name),
	}


def _create_cross_docking_order(dk_doc: Any, row: Any, detail_idx: int) -> dict[str, Any]:
	order = frappe.new_doc("Cross-Docking Order")
	_apply_docket_context(order, dk_doc)
	if frappe.get_meta("Cross-Docking Order").get_field("order_date"):
		order.order_date = today()
	apply_internal_job_detail_row_to_operational_doc(order, row, overwrite=True)
	_copy_docket_packages_to_target(dk_doc, order)
	_prepare_charges_before_insert(dk_doc, order, row)
	order.insert(ignore_permissions=True)
	_persist_row_link(dk_doc.name, "Cross-Docking Order", order.name, detail_idx)
	frappe.db.commit()
	return {
		"cross_docking_order": order.name,
		"message": _("Cross-Docking Order {0} created.").format(order.name),
	}


def _populate_mice_order_charges_from_sales_quote(target_doc: Any, row: Any | None) -> None:
	"""Copy matching MICE Sales Quote charge lines onto a MICE Order."""
	from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal
	from logistics.utils.sales_quote_charge_parameters import (
		extract_service_scoped_quote_parameters,
		sales_quote_charge_row_matches_internal_job_detail_params,
	)
	from logistics.utils.sales_quote_programme_charges import map_sales_quote_charge_to_programme_charge_dict

	sq_name = (getattr(target_doc, "sales_quote", None) or "").strip()
	if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
		return
	st = (getattr(row, "service_type", None) or "MICE").strip() if row else "MICE"
	ij_params = extract_service_scoped_quote_parameters(row, st) if row else {}
	sq = frappe.get_doc("Sales Quote", sq_name)
	charge_dt = "MICE Project Charges"
	target_doc.set("charges", [])
	for ch in sq.get("charges") or []:
		if not sales_quote_charge_service_types_equal(getattr(ch, "service_type", None), st):
			continue
		if ij_params and not sales_quote_charge_row_matches_internal_job_detail_params(ch, ij_params):
			continue
		mapped = map_sales_quote_charge_to_programme_charge_dict(ch, sq_name, charge_dt)
		if mapped:
			target_doc.append("charges", mapped)


def _resolve_exhibit_lifecycle_stage(exhibit_name: str | None) -> str:
	exhibit_name = (exhibit_name or "").strip()
	if exhibit_name and frappe.db.exists("MICE Project", exhibit_name):
		stage = frappe.db.get_value("MICE Project", exhibit_name, "lifecycle_stage")
		if stage:
			return stage
	from logistics.utils.lifecycle_stage import FOR_EXHIBITS, resolve_default_lifecycle_stage

	return resolve_default_lifecycle_stage(module_filter=FOR_EXHIBITS, preferred="Pre-Show")


def _suggested_mice_order_title_from_docket(dk_doc: Any, row: Any | None) -> str:
	if row:
		desc = (getattr(row, "job_description", None) or "").strip()
		if desc:
			return desc
	label = (getattr(dk_doc, "exhibitor_name", None) or dk_doc.name or "").strip()
	return f"{label} — {_('MICE')}" if label else _("MICE Order")


def _create_mice_order(dk_doc: Any, row: Any, detail_idx: int) -> dict[str, Any]:
	exhibit_name = (getattr(dk_doc, "exhibit", None) or "").strip()
	if not exhibit_name:
		frappe.throw(_("Link this Docket to a MICE Project before creating a MICE Order."))

	order = frappe.new_doc("MICE Order")
	order.exhibit = exhibit_name
	order.lifecycle_stage = _resolve_exhibit_lifecycle_stage(exhibit_name)
	order.order_title = _suggested_mice_order_title_from_docket(dk_doc, row)
	if order.meta.get_field("order_date"):
		order.order_date = today()
	if order.meta.get_field("status"):
		order.status = "Draft"

	_apply_docket_context(order, dk_doc)
	if row and order.meta.get_field("site"):
		site = (getattr(row, "sp_site", None) or "").strip()
		if site:
			order.site = site

	apply_internal_job_detail_row_to_operational_doc(order, row, overwrite=True)
	_copy_docket_packages_to_target(dk_doc, order)
	_prepare_charges_before_insert(dk_doc, order, row)
	if not (order.get("charges") or []):
		_populate_mice_order_charges_from_sales_quote(order, row)
	order.insert(ignore_permissions=True)
	_persist_row_link(dk_doc.name, "MICE Order", order.name, detail_idx)
	frappe.db.commit()
	return {
		"mice_order": order.name,
		"message": _("MICE Order {0} created.").format(order.name),
	}


_CREATE_DISPATCH = {
	"Air Booking": _create_air_booking,
	"Sea Booking": _create_sea_booking,
	"Transport Order": _create_transport_order,
	"Declaration Order": _create_declaration_order,
	"Inbound Order": _create_inbound_order,
	"Cross-Docking Order": _create_cross_docking_order,
	"MICE Order": _create_mice_order,
}


@frappe.whitelist()
def create_booking_or_order_from_docket(
	docket: str,
	job_type: str,
	internal_job_idx: int | None = None,
	internal_jobs: Any = None,
	linked_services: Any = None,
):
	"""Create the chosen booking/order from the matching Linked Service row on the Docket."""
	if not docket or not frappe.db.exists("Docket", docket):
		frappe.throw(_("Invalid Docket."))
	jt = (job_type or "").strip()
	if jt not in DOCKET_CREATABLE_JOB_TYPES:
		frappe.throw(_("Invalid job type."))

	dk_doc = frappe.get_doc("Docket", docket)
	dk_doc.check_permission("write")

	idx = coerce_internal_job_detail_idx(internal_job_idx)

	client_rows = _resolve_client_rows(internal_jobs, linked_services)
	with _client_rows_context(client_rows):
		from logistics.utils.internal_job_persistence import (
			ensure_linked_service_rows_materialized,
		)

		ensure_linked_service_rows_materialized(dk_doc)
		row, resolved_idx = _resolve_row_for_create(dk_doc, jt, idx)
		if row is None:
			frappe.throw(
				_(
					"No matching Services row for {0}. Link a Sales Quote with subsidiary services first."
				).format(jt)
			)
		if resolved_idx is None:
			frappe.throw(_("Could not resolve the Linked Service row to update after creation."))
		from logistics.utils.internal_job_creation_eligibility import (
			require_internal_job_creation_eligible,
		)

		require_internal_job_creation_eligible(
			sales_quote=getattr(dk_doc, "sales_quote", None),
			parent_doc=dk_doc,
			ij_row=row,
			service_type_label=(getattr(row, "service_type", None) or "").strip(),
		)
		handler = _CREATE_DISPATCH[jt]
		return handler(dk_doc, row, resolved_idx)
