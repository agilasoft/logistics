# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Push Change Request charge lines to the linked job (cost) on CR submit; link rows for later Sales Quote revenue merge."""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint, flt

from logistics.pricing_center.additional_charge_to_job import (
	INTERNAL_JOB_SATELLITE_JOB_TYPES,
	JOB_TYPE_TO_SERVICE,
	MAIN_JOB_TYPES_FOR_CHANGE_REQUEST,
	_amendment_family_names,
	_row_val,
)
from logistics.utils.linked_service_compat import (
	CHARGE_SCOPE_LINKED,
	charge_row_linked_service_link,
	linked_service_detail_doctype,
	set_charge_row_linked_service_link,
)
from logistics.utils.sales_quote_charge_copy import stamp_scope_fields_on_charge_row

# Backward-compatible alias for declaration-only checks elsewhere in this module.
_DECLARATION_JOB_TYPES = frozenset({"Declaration", "Declaration Order"})

# When the Change Request targets an Internal Job satellite booking, we reuse the Main-side
# mapper of the matching service to map a Change Request Charge row into the satellite's
# charge child table (the schemas are intentionally parallel: Sea Booking Charges mirror
# Sea Shipment Charges, etc.). ``_safe_append_charge_to_doc`` strips fields that the
# specific destination child table doesn't expose.
_SATELLITE_TO_MAIN_MAPPER_JOB_TYPE = {
	"Transport Order": "Transport Job",
	"Sea Booking": "Sea Shipment",
	"Air Booking": "Air Shipment",
	"Declaration Order": "Declaration",
	"Inbound Order": "Warehouse Job",
	"Release Order": "Warehouse Job",
}


def _job_currency(job_doc):
	return (
		getattr(job_doc, "currency", None)
		or frappe.defaults.get_global_default("currency")
		or frappe.db.get_single_value("Global Defaults", "default_currency")
	)


def _remove_job_charges_for_change_request(job_doc, change_request_name):
	if not job_doc.get("charges"):
		return
	for row in list(job_doc.charges):
		if getattr(row, "change_request", None) == change_request_name:
			job_doc.remove(row)


def _map_cr_charge_to_air_cost(row, cr_name, charge_row_name):
	qty = flt(_row_val(row, "cost_quantity"), 2)
	if not qty:
		qty = 1
	rev_qty = flt(_row_val(row, "quantity"), 2) or 1
	ccy = _row_val(row, "currency") or _row_val(row, "cost_currency")
	item_name = _row_val(row, "item_name") or ""
	return {
		"service_type": _row_val(row, "service_type") or "Air",
		"item_code": _row_val(row, "item_code"),
		"charge_type": "Margin",
		"charge_category": _row_val(row, "charge_category") or "Other",
		"revenue_calculation_method": _row_val(row, "calculation_method") or "Flat Rate",
		"quantity": rev_qty,
		"uom": _row_val(row, "uom"),
		"currency": ccy,
		"unit_rate": 0,
		"unit_type": _row_val(row, "unit_type"),
		"minimum_quantity": flt(_row_val(row, "minimum_quantity"), 2),
		"minimum_charge": flt(_row_val(row, "minimum_charge"), 2),
		"maximum_charge": flt(_row_val(row, "maximum_charge"), 2),
		"base_amount": 0,
		"estimated_revenue": 0,
		"bill_to": _row_val(row, "bill_to"),
		"description": item_name,
		"cost_calculation_method": _row_val(row, "cost_calculation_method") or "Flat Rate",
		"cost_quantity": qty,
		"cost_uom": _row_val(row, "cost_uom"),
		"cost_currency": _row_val(row, "cost_currency") or ccy,
		"unit_cost": flt(_row_val(row, "unit_cost"), 2),
		"cost_unit_type": _row_val(row, "cost_unit_type"),
		"cost_minimum_quantity": flt(_row_val(row, "cost_minimum_quantity"), 2),
		"cost_minimum_charge": flt(_row_val(row, "cost_minimum_charge"), 2),
		"cost_maximum_charge": flt(_row_val(row, "cost_maximum_charge"), 2),
		"cost_base_amount": flt(_row_val(row, "cost_base_amount"), 2),
		"estimated_cost": flt(_row_val(row, "estimated_cost"), 2),
		"pay_to": _row_val(row, "pay_to"),
		"revenue_calc_notes": "",
		"cost_calc_notes": _row_val(row, "cost_calc_notes") or "",
		"change_request": cr_name,
		"change_request_charge": charge_row_name,
	}


def _map_cr_charge_to_transport_cost(row, cr_name, charge_row_name):
	qty = flt(_row_val(row, "cost_quantity"), 2)
	if not qty:
		qty = 1
	rev_qty = flt(_row_val(row, "quantity"), 2) or 1
	ccy = _row_val(row, "currency") or _row_val(row, "cost_currency")
	return {
		"service_type": _row_val(row, "service_type") or "Transport",
		"item_code": _row_val(row, "item_code"),
		"charge_type": "Margin",
		"charge_category": _row_val(row, "charge_category") or "Other",
		"revenue_calculation_method": _row_val(row, "calculation_method") or "Flat Rate",
		"quantity": rev_qty,
		"uom": _row_val(row, "uom"),
		"currency": ccy,
		"unit_rate": 0,
		"unit_type": _row_val(row, "unit_type"),
		"minimum_quantity": flt(_row_val(row, "minimum_quantity"), 2),
		"minimum_charge": flt(_row_val(row, "minimum_charge"), 2),
		"maximum_charge": flt(_row_val(row, "maximum_charge"), 2),
		"base_amount": 0,
		"estimated_revenue": 0,
		"bill_to": _row_val(row, "bill_to"),
		"cost_calculation_method": _row_val(row, "cost_calculation_method") or "Flat Rate",
		"cost_quantity": qty,
		"cost_uom": _row_val(row, "cost_uom"),
		"cost_currency": _row_val(row, "cost_currency") or ccy,
		"unit_cost": flt(_row_val(row, "unit_cost"), 2),
		"cost_unit_type": _row_val(row, "cost_unit_type"),
		"cost_minimum_quantity": flt(_row_val(row, "cost_minimum_quantity"), 2),
		"cost_minimum_charge": flt(_row_val(row, "cost_minimum_charge"), 2),
		"cost_maximum_charge": flt(_row_val(row, "cost_maximum_charge"), 2),
		"cost_base_amount": flt(_row_val(row, "cost_base_amount"), 2),
		"estimated_cost": flt(_row_val(row, "estimated_cost"), 2),
		"pay_to": _row_val(row, "pay_to"),
		"revenue_calc_notes": "",
		"cost_calc_notes": _row_val(row, "cost_calc_notes") or "",
		"change_request": cr_name,
		"change_request_charge": charge_row_name,
	}


def _map_cr_charge_to_warehouse_cost(row, cr_name, charge_row_name, job_doc):
	ccy = _row_val(row, "currency") or _row_val(row, "cost_currency") or _job_currency(job_doc)
	rev_qty = flt(_row_val(row, "quantity"), 2) or 1
	return {
		"item_code": _row_val(row, "item_code"),
		"charge_type": "Margin",
		"charge_category": _row_val(row, "charge_category") or "Other",
		"service_type": "Warehousing",
		"quantity": rev_qty,
		"uom": _row_val(row, "uom") or _row_val(row, "cost_uom"),
		"currency": ccy,
		"unit_rate": 0,
		"estimated_revenue": 0,
		"estimated_cost": flt(_row_val(row, "estimated_cost"), 2),
		"change_request": cr_name,
		"change_request_charge": charge_row_name,
	}


def _map_cr_charge_to_sea_cost(row, cr_name, charge_row_name):
	qty = flt(_row_val(row, "cost_quantity"), 2)
	if not qty:
		qty = 1
	rev_qty = flt(_row_val(row, "quantity"), 2) or 1
	ccy = _row_val(row, "currency") or _row_val(row, "cost_currency")
	ic = _row_val(row, "item_code")
	item_name = ""
	if ic:
		item_name = frappe.db.get_value("Item", ic, "item_name") or ""
	return {
		"service_type": _row_val(row, "service_type") or "Sea",
		"item_code": ic,
		"charge_type": "Margin",
		"charge_category": _row_val(row, "charge_category") or "Other",
		"revenue_calculation_method": _row_val(row, "calculation_method") or "Flat Rate",
		"quantity": rev_qty,
		"uom": _row_val(row, "uom"),
		"currency": ccy,
		"selling_currency": ccy,
		"buying_currency": _row_val(row, "cost_currency") or ccy,
		"unit_rate": 0,
		"unit_type": _row_val(row, "unit_type"),
		"minimum_quantity": flt(_row_val(row, "minimum_quantity"), 2),
		"minimum_charge": flt(_row_val(row, "minimum_charge"), 2),
		"maximum_charge": flt(_row_val(row, "maximum_charge"), 2),
		"base_amount": 0,
		"estimated_revenue": 0,
		"bill_to": _row_val(row, "bill_to"),
		"description": item_name,
		"cost_calculation_method": _row_val(row, "cost_calculation_method") or "Flat Rate",
		"cost_quantity": qty,
		"cost_uom": _row_val(row, "cost_uom"),
		"cost_currency": _row_val(row, "cost_currency") or ccy,
		"unit_cost": flt(_row_val(row, "unit_cost"), 2),
		"cost_unit_type": _row_val(row, "cost_unit_type"),
		"cost_minimum_quantity": flt(_row_val(row, "cost_minimum_quantity"), 2),
		"cost_minimum_charge": flt(_row_val(row, "cost_minimum_charge"), 2),
		"cost_maximum_charge": flt(_row_val(row, "cost_maximum_charge"), 2),
		"cost_base_amount": flt(_row_val(row, "cost_base_amount"), 2),
		"estimated_cost": flt(_row_val(row, "estimated_cost"), 2),
		"pay_to": _row_val(row, "pay_to"),
		"revenue_calc_notes": "",
		"cost_calc_notes": _row_val(row, "cost_calc_notes") or "",
		"change_request": cr_name,
		"change_request_charge": charge_row_name,
	}


def _map_cr_charge_to_declaration_cost(row, cr_name, charge_row_name):
	qty = flt(_row_val(row, "cost_quantity"), 2)
	if not qty:
		qty = 1
	rev_qty = flt(_row_val(row, "quantity"), 2) or 1
	ccy = _row_val(row, "currency") or _row_val(row, "cost_currency")
	rev_method = _row_val(row, "calculation_method") or "Fixed Amount"
	cost_method = _row_val(row, "cost_calculation_method") or "Fixed Amount"
	return {
		"service_type": _row_val(row, "service_type") or "Customs",
		"item_code": _row_val(row, "item_code"),
		"charge_type": "Margin",
		"charge_category": _row_val(row, "charge_category") or "Other",
		"revenue_calculation_method": rev_method,
		"quantity": rev_qty,
		"uom": _row_val(row, "uom"),
		"currency": ccy,
		"selling_currency": ccy,
		"buying_currency": _row_val(row, "cost_currency") or ccy,
		"unit_rate": 0,
		"unit_type": _row_val(row, "unit_type"),
		"minimum_quantity": flt(_row_val(row, "minimum_quantity"), 2),
		"minimum_charge": flt(_row_val(row, "minimum_charge"), 2),
		"maximum_charge": flt(_row_val(row, "maximum_charge"), 2),
		"base_amount": 0,
		"estimated_revenue": 0,
		"bill_to": _row_val(row, "bill_to"),
		"charge_description": _row_val(row, "item_name") or "",
		"cost_calculation_method": cost_method,
		"cost_quantity": qty,
		"cost_uom": _row_val(row, "cost_uom"),
		"cost_currency": _row_val(row, "cost_currency") or ccy,
		"unit_cost": flt(_row_val(row, "unit_cost"), 2),
		"cost_unit_type": _row_val(row, "cost_unit_type"),
		"cost_minimum_quantity": flt(_row_val(row, "cost_minimum_quantity"), 2),
		"cost_minimum_charge": flt(_row_val(row, "cost_minimum_charge"), 2),
		"cost_maximum_charge": flt(_row_val(row, "cost_maximum_charge"), 2),
		"cost_base_amount": flt(_row_val(row, "cost_base_amount"), 2),
		"estimated_cost": flt(_row_val(row, "estimated_cost"), 2),
		"pay_to": _row_val(row, "pay_to"),
		"revenue_calc_notes": "",
		"cost_calc_notes": _row_val(row, "cost_calc_notes") or "",
		"change_request": cr_name,
		"change_request_charge": charge_row_name,
	}


def _map_cr_charge_to_special_project_cost(row, cr_name, charge_row_name):
	from logistics.utils.sales_quote_charge_parameters import merge_charge_row_parameters_onto_dict

	qty = flt(_row_val(row, "cost_quantity"), 2)
	if not qty:
		qty = 1
	rev_qty = flt(_row_val(row, "quantity"), 2) or 1
	ccy = _row_val(row, "currency") or _row_val(row, "cost_currency")
	ic = _row_val(row, "item_code")
	item_name = _row_val(row, "item_name") or ""
	if ic and not item_name:
		item_name = frappe.db.get_value("Item", ic, "item_name") or ""
	out = {
		"service_type": _row_val(row, "service_type") or "Special Project",
		"item_code": ic,
		"charge_type": "Margin",
		"charge_category": _row_val(row, "charge_category") or "Other",
		"revenue_calculation_method": _row_val(row, "calculation_method") or "Flat Rate",
		"quantity": rev_qty,
		"uom": _row_val(row, "uom"),
		"currency": ccy,
		"selling_currency": ccy,
		"buying_currency": _row_val(row, "cost_currency") or ccy,
		"unit_rate": 0,
		"unit_type": _row_val(row, "unit_type"),
		"minimum_quantity": flt(_row_val(row, "minimum_quantity"), 2),
		"minimum_charge": flt(_row_val(row, "minimum_charge"), 2),
		"maximum_charge": flt(_row_val(row, "maximum_charge"), 2),
		"base_amount": 0,
		"estimated_revenue": 0,
		"bill_to": _row_val(row, "bill_to"),
		"description": item_name,
		"cost_calculation_method": _row_val(row, "cost_calculation_method") or "Flat Rate",
		"cost_quantity": qty,
		"cost_uom": _row_val(row, "cost_uom"),
		"cost_currency": _row_val(row, "cost_currency") or ccy,
		"unit_cost": flt(_row_val(row, "unit_cost"), 2),
		"cost_unit_type": _row_val(row, "cost_unit_type"),
		"cost_minimum_quantity": flt(_row_val(row, "cost_minimum_quantity"), 2),
		"cost_minimum_charge": flt(_row_val(row, "cost_minimum_charge"), 2),
		"cost_maximum_charge": flt(_row_val(row, "cost_maximum_charge"), 2),
		"cost_base_amount": flt(_row_val(row, "cost_base_amount"), 2),
		"estimated_cost": flt(_row_val(row, "estimated_cost"), 2),
		"pay_to": _row_val(row, "pay_to"),
		"revenue_calc_notes": "",
		"cost_calc_notes": _row_val(row, "cost_calc_notes") or "",
		"change_request": cr_name,
		"change_request_charge": charge_row_name,
	}
	merge_charge_row_parameters_onto_dict(row, out, "Special Project Charges")
	return out


def _cost_mappers():
	return {
		"Air Shipment": _map_cr_charge_to_air_cost,
		"Transport Job": _map_cr_charge_to_transport_cost,
		"Warehouse Job": _map_cr_charge_to_warehouse_cost,
		"Sea Shipment": _map_cr_charge_to_sea_cost,
		"Declaration": _map_cr_charge_to_declaration_cost,
		"Declaration Order": _map_cr_charge_to_declaration_cost,
		"Special Project": _map_cr_charge_to_special_project_cost,
	}


# ---------------------------------------------------------------------------
# Main ↔ Internal Job satellite resolution helpers
# ---------------------------------------------------------------------------


def _resolve_main_and_default_internal_job(cr_doc):
	"""Return ``(main_job_type, main_job_name, default_internal_job_or_None)`` for the CR target.

	* CR target is a Main job → the Main is the target itself; default internal_job is ``None``.
	* CR target is an IJ satellite booking → walks ``main_service_type`` / ``main_service`` back-links
	  to the parent Main and exposes the satellite's ``linked_service`` link as the default IJ to tag
	  all rows with (when an individual CR Charge row doesn't carry its own ``internal_job`` value).

	Returns ``(None, None, None)`` when the target is misconfigured (missing back-links, satellite
	not Linked, or the parent main job no longer exists).
	"""
	from logistics.utils.service_role_rules import (
		get_linked_service_name,
		get_main_service_name,
		get_main_service_type,
		is_linked_service_satellite,
	)

	if not cr_doc.job_type or not cr_doc.job:
		return None, None, None
	if cr_doc.job_type in MAIN_JOB_TYPES_FOR_CHANGE_REQUEST:
		return cr_doc.job_type, cr_doc.job, None
	if cr_doc.job_type in INTERNAL_JOB_SATELLITE_JOB_TYPES:
		if not frappe.db.exists(cr_doc.job_type, cr_doc.job):
			return None, None, None
		sat = (
			frappe.db.get_value(
				cr_doc.job_type,
				cr_doc.job,
				(
					"service_role",
					"main_service_type",
					"main_service",
					"linked_service",
				),
				as_dict=True,
			)
			or {}
		)
		if not is_linked_service_satellite(sat):
			# Satellite booking that isn't Linked — treat as standalone, no Main mirroring.
			return None, None, None
		mt = get_main_service_type(sat)
		mn = get_main_service_name(sat)
		ij = get_linked_service_name(sat)
		if not mt or not mn or not frappe.db.exists(mt, mn):
			return None, None, None
		return mt, mn, ij or None
	return None, None, None


def _satellite_for_internal_job(main_job_type, main_job, internal_job_name):
	"""Locate the operational satellite booking materialised from a given Linked Service under a Main job.

	Returns ``(satellite_doctype, satellite_name)`` or ``(None, None)`` when no satellite exists
	(the Linked Service Detail row may not have been materialised into an actual booking yet).
	"""
	ls = (internal_job_name or "").strip()
	if not ls or not main_job_type or not main_job:
		return None, None
	detail_dt = linked_service_detail_doctype()
	try:
		detail_meta = frappe.get_meta(detail_dt)
	except Exception:
		return None, None
	link_field = "linked_service" if detail_meta.has_field("linked_service") else "internal_job"
	rows = frappe.get_all(
		detail_dt,
		filters={
			"parent": main_job,
			"parenttype": main_job_type,
			link_field: ls,
		},
		fields=["job_type", "job_no"],
		limit=1,
	)
	for row in rows:
		jt = (row.get("job_type") or "").strip()
		jn = (row.get("job_no") or "").strip()
		if jt and jn and frappe.db.exists(jt, jn):
			return jt, jn
	return None, None


def _child_doctype_for_charges_table(parent_doctype):
	try:
		meta = frappe.get_meta(parent_doctype)
	except Exception:
		return None
	df = meta.get_field("charges")
	if not df or df.fieldtype != "Table":
		return None
	return (df.options or "").strip() or None


def _safe_append_charge_to_doc(target_doc, raw_dict):
	"""Append a charge dict to ``target_doc.charges``.

	When the destination child table's metadata is available, fields it does not expose are
	scrubbed first (Sea Booking Charges, Air Booking Charges, etc. share most fields with their
	main-job siblings but not all). When meta is unavailable — e.g. unit tests passing a
	``MagicMock`` document — the dict is appended as-is so the existing main-job code path stays
	wire-compatible with the previous implementation.

	After ``append``, the resulting row's ``charge_scope`` / ``linked_service`` are re-stamped from
	the raw dict (when present) to guarantee they survive any default value the destination's
	schema may apply (``Main`` is the default for ``charge_scope`` on every booking child table).

	Returns ``True`` when a row was appended (the payload must have an ``item_code``).
	"""
	if not raw_dict or not raw_dict.get("item_code"):
		return False
	payload = raw_dict
	child = _child_doctype_for_charges_table(target_doc.doctype)
	if child:
		try:
			meta = frappe.get_meta(child)
			valid = {f.fieldname for f in meta.fields}
			payload = {k: v for k, v in raw_dict.items() if k in valid and v is not None and v != ""}
		except Exception:
			payload = raw_dict
	appended = target_doc.append("charges", payload)
	# Force scope / linked-service onto the appended row in case Frappe applied schema defaults.
	scope_val = raw_dict.get("charge_scope")
	ls_val = charge_row_linked_service_link(raw_dict)
	if appended is not None:
		if scope_val and hasattr(appended, "charge_scope"):
			stamp_scope_fields_on_charge_row(appended, scope_val, ls_val)
		elif ls_val:
			stamp_scope_fields_on_charge_row(appended, CHARGE_SCOPE_LINKED, ls_val)
	return True


def _produce_cost_dict_for_target(cr_doc, row, target_job_type, target_job_doc):
	"""Map a Change Request Charge row → a cost-row dict appropriate for ``target_job_type``.

	IJ-satellite destinations reuse the mapper of their service-equivalent Main (Sea Booking →
	Sea Shipment mapper, etc.); ``_safe_append_charge_to_doc`` later strips fields not present on
	the destination child schema.
	"""
	from logistics.utils.sales_quote_charge_parameters import effective_change_request_charge_row

	row = effective_change_request_charge_row(row, cr_doc)
	mappers = _cost_mappers()
	mapper_key = _SATELLITE_TO_MAIN_MAPPER_JOB_TYPE.get(target_job_type, target_job_type)
	fn = mappers.get(mapper_key)
	if not fn:
		return None
	if mapper_key == "Warehouse Job":
		return fn(row, cr_doc.name, row.name, target_job_doc)
	return fn(row, cr_doc.name, row.name)


def _cr_charge_linked_service_map(cr_doc):
	return {
		(c.name or ""): charge_row_linked_service_link(c)
		for c in (cr_doc.get("charges") or [])
	}


def _linked_service_names_from_cr_doc(cr_doc, default_linked_service=None):
	names = set()
	for row in cr_doc.get("charges") or []:
		ls = charge_row_linked_service_link(row)
		if ls:
			names.add(ls)
	default_ls = (default_linked_service or "").strip()
	if default_ls:
		names.add(default_ls)
	return names


def _restamp_linked_scope_on_charge_row(row, linked_service_name):
	"""Re-assert Linked scope + linked_service link on a charge row. Returns True if changed."""
	if not linked_service_name:
		return False
	changed = False
	if hasattr(row, "charge_scope"):
		current_scope = getattr(row, "charge_scope", None)
		if (current_scope or "").strip() != CHARGE_SCOPE_LINKED:
			stamp_scope_fields_on_charge_row(row, CHARGE_SCOPE_LINKED, linked_service_name)
			changed = True
		elif charge_row_linked_service_link(row) != linked_service_name:
			stamp_scope_fields_on_charge_row(row, CHARGE_SCOPE_LINKED, linked_service_name)
			changed = True
	elif isinstance(row, dict):
		stamp_scope_fields_on_charge_row(row, CHARGE_SCOPE_LINKED, linked_service_name)
		changed = True
	return changed


def _linked_service_for_row(row, default_linked_service=None):
	"""Pick the Linked Service tag for a CR Charge row: row-level wins, else the CR default."""
	from logistics.utils.linked_service_compat import CHARGE_SCOPE_MAIN, normalize_charge_scope

	scope = normalize_charge_scope(getattr(row, "charge_scope", None))
	ls = charge_row_linked_service_link(row)
	if ls:
		return ls
	if scope == CHARGE_SCOPE_MAIN:
		return None
	return ((default_linked_service or "").strip() or None)


# Backward-compatible alias.
_internal_job_for_row = _linked_service_for_row


def _decorate_charge_dict_with_linked_service_scope(charge_dict, target_doc, linked_service_name):
	"""Mark a charge dict as Linked-service-scoped when the destination supports those columns.

	Sets ``charge_scope='Linked'`` and ``linked_service=<X>`` explicitly (not via setdefault).
	Direct assignment guarantees that even if an upstream mapper accidentally produced a
	``charge_scope`` value (e.g. ``Main`` inherited from a row copy), it gets overridden so the
	linked-service row is always tagged correctly. Silently skipped on tables that don't expose
	``charge_scope`` (e.g. Special Project Charges).
	"""
	if not linked_service_name:
		return charge_dict
	child = _child_doctype_for_charges_table(target_doc.doctype)
	if not child:
		return charge_dict
	try:
		meta = frappe.get_meta(child)
	except Exception:
		return charge_dict
	valid = {f.fieldname for f in meta.fields}
	if "charge_scope" in valid:
		charge_dict["charge_scope"] = CHARGE_SCOPE_LINKED
	set_charge_row_linked_service_link(charge_dict, linked_service_name)
	return charge_dict


# Backward-compatible alias.
_decorate_charge_dict_with_internal_job_scope = _decorate_charge_dict_with_linked_service_scope


# ---------------------------------------------------------------------------
# Main entry points: apply / remove with bidirectional Main ↔ Satellite mirror
# ---------------------------------------------------------------------------


def _change_request_charge_row_names(cr_doc):
	return {
		(_row_val(r, "name") or "").strip()
		for r in (cr_doc.get("charges") or [])
		if _row_val(r, "item_code")
	}


def change_request_cost_rows_missing_on_main_job(cr_doc):
	"""True when submitted CR charge rows are not all present on the Main job."""
	crc_names = _change_request_charge_row_names(cr_doc)
	if not crc_names:
		return False
	main_job_type, main_job_name, _ = _resolve_main_and_default_internal_job(cr_doc)
	if not main_job_type or not main_job_name:
		return False
	if not frappe.db.exists(main_job_type, main_job_name):
		return False
	job_doc = frappe.get_doc(main_job_type, main_job_name)
	found = {
		(getattr(row, "change_request_charge", None) or "").strip()
		for row in (job_doc.get("charges") or [])
		if getattr(row, "change_request", None) == cr_doc.name
	}
	return not crc_names.issubset(found)


def ensure_change_request_cost_rows_on_job(cr_doc):
	"""Idempotently apply CR cost rows when any are missing from the Main job."""
	if change_request_cost_rows_missing_on_main_job(cr_doc):
		apply_change_request_charges_to_job(cr_doc)


def apply_change_request_charges_to_job(cr_doc):
	"""On Change Request submit: append cost rows to the Main job AND mirror to Internal Job satellites.

	Behaviour:
	* Any prior rows tagged with this Change Request name (``charges.change_request == cr_doc.name``)
	  are first removed from the Main and every related satellite (idempotent re-apply on amendments).
	* For each Change Request Charge row:
	  - A cost row is appended to the **Main** job's ``charges`` table, tagged with
	    ``change_request`` + ``change_request_charge``. When the row carries an Internal Job tag
	    (or the CR target is an IJ satellite and the row inherits the satellite's IJ), the Main
	    row is additionally scoped with ``charge_scope='Internal Job'`` + ``internal_job=<X>``.
	  - When the row has an Internal Job tag, a parallel cost row is appended to the **satellite
	    booking** materialised from that Internal Job (Transport Order / Sea Booking / Air Booking /
	    Declaration Order / Inbound Order / Release Order). The satellite row carries the same
	    ``change_request`` + ``change_request_charge`` tags so cancel can remove them cleanly.
	"""
	if not getattr(cr_doc, "job_type", None) or not getattr(cr_doc, "job", None):
		return
	if not frappe.db.exists(cr_doc.job_type, cr_doc.job):
		frappe.throw(_("Job {0} does not exist").format(cr_doc.job))
	if not cr_doc.get("charges"):
		frappe.msgprint(_("No charge lines on this Change Request; nothing was applied to the job."), indicator="orange")
		return

	main_job_type, main_job_name, default_ij = _resolve_main_and_default_internal_job(cr_doc)
	if not main_job_type or not main_job_name:
		frappe.msgprint(
			_(
				"Change Request job {0} is not linked to a Main job. "
				"Internal Job satellites must carry main_service_type / main_service back-links."
			).format(cr_doc.job),
			indicator="orange",
		)
		return

	expected_service = JOB_TYPE_TO_SERVICE.get(main_job_type)
	if not expected_service:
		frappe.msgprint(
			_("Change Request job type {0} is not configured for applying charges.").format(main_job_type),
			indicator="orange",
		)
		return

	main_job_doc = frappe.get_doc(main_job_type, main_job_name)

	# Idempotent re-apply: drop any rows previously tagged with this CR from the Main first.
	_remove_job_charges_for_change_request(main_job_doc, cr_doc.name)

	# Track satellite docs we touch so we can save them once at the end (and so we drop prior
	# rows once per satellite). Keyed by ``(doctype, name)``.
	satellites_touched = {}
	added_main = 0
	added_satellites = 0

	for row in cr_doc.charges:
		if not _row_val(row, "item_code"):
			continue

		ij_tag = _linked_service_for_row(row, default_ij)

		# --- Main side ----------------------------------------------------------------
		main_dict = _produce_cost_dict_for_target(cr_doc, row, main_job_type, main_job_doc)
		if main_dict:
			_decorate_charge_dict_with_linked_service_scope(main_dict, main_job_doc, ij_tag)
			if _safe_append_charge_to_doc(main_job_doc, main_dict):
				added_main += 1

		# --- Satellite side -----------------------------------------------------------
		if not ij_tag:
			continue
		sat_type, sat_name = _satellite_for_internal_job(main_job_type, main_job_name, ij_tag)
		if not sat_type or not sat_name:
			# IJ exists on the row but no satellite booking has been materialised yet — skip
			# silently; the Main row already carries the IJ-scoped tag so it will surface on
			# the satellite the next time charges are populated from Main.
			continue
		key = (sat_type, sat_name)
		sat_doc = satellites_touched.get(key)
		if sat_doc is None:
			sat_doc = frappe.get_doc(sat_type, sat_name)
			_remove_job_charges_for_change_request(sat_doc, cr_doc.name)
			satellites_touched[key] = sat_doc
		sat_dict = _produce_cost_dict_for_target(cr_doc, row, sat_type, sat_doc)
		if sat_dict:
			# Satellite row already implicitly scoped to its IJ (it lives on the satellite).
			# Still set the tag explicitly when the child supports it for clarity / filtering.
			_decorate_charge_dict_with_linked_service_scope(sat_dict, sat_doc, ij_tag)
			if _safe_append_charge_to_doc(sat_doc, sat_dict):
				added_satellites += 1

	main_job_doc.flags.ignore_validate_update_after_submit = True
	main_job_doc.save(ignore_permissions=True)
	for sat_doc in satellites_touched.values():
		sat_doc.flags.ignore_validate_update_after_submit = True
		sat_doc.save(ignore_permissions=True)

	if added_main > 0 and added_satellites > 0:
		frappe.msgprint(
			_(
				"Added {0} cost charge line(s) from Change Request {1} to Main job {2} "
				"and {3} mirrored line(s) across {4} Internal Job satellite booking(s)."
			).format(
				added_main,
				cr_doc.name,
				main_job_name,
				added_satellites,
				len(satellites_touched),
			),
			indicator="green",
		)
	elif added_main > 0:
		frappe.msgprint(
			_("Added {0} cost charge line(s) from Change Request {1} to {2}.").format(
				added_main, cr_doc.name, main_job_name
			),
			indicator="green",
		)


def remove_change_request_charges_from_job(cr_doc):
	"""On Change Request cancel: remove rows from the Main job AND every linked satellite booking."""
	if not getattr(cr_doc, "job_type", None) or not getattr(cr_doc, "job", None):
		return
	if not frappe.db.exists(cr_doc.job_type, cr_doc.job):
		return

	main_job_type, main_job_name, default_ij = _resolve_main_and_default_internal_job(cr_doc)
	if not main_job_type or not main_job_name:
		# Last-resort: try removing on the CR target itself even if Main resolution failed.
		try:
			job_doc = frappe.get_doc(cr_doc.job_type, cr_doc.job)
		except frappe.DoesNotExistError:
			return
		_remove_job_charges_for_change_request(job_doc, cr_doc.name)
		job_doc.flags.ignore_validate_update_after_submit = True
		job_doc.save(ignore_permissions=True)
		return

	main_doc = frappe.get_doc(main_job_type, main_job_name)
	_remove_job_charges_for_change_request(main_doc, cr_doc.name)
	main_doc.flags.ignore_validate_update_after_submit = True
	main_doc.save(ignore_permissions=True)

	# Walk every satellite that may have received a mirrored row. The set of IJs to clean up is
	# the union of (a) IJs explicitly tagged on the CR's own charge rows and (b) the satellite's
	# own IJ when the CR target was a satellite.
	ij_names = _linked_service_names_from_cr_doc(cr_doc, default_ij)
	for ij in ij_names:
		sat_type, sat_name = _satellite_for_internal_job(main_job_type, main_job_name, ij)
		if not sat_type or not sat_name:
			continue
		sat_doc = frappe.get_doc(sat_type, sat_name)
		_remove_job_charges_for_change_request(sat_doc, cr_doc.name)
		sat_doc.flags.ignore_validate_update_after_submit = True
		sat_doc.save(ignore_permissions=True)


def _find_change_request_job_row(job_doc, cr_name, charge_row_name):
	for row in job_doc.get("charges") or []:
		if getattr(row, "change_request", None) == cr_name and getattr(row, "change_request_charge", None) == charge_row_name:
			return row
	return None


def _apply_sq_revenue_to_air_job_row(job_row, sq_row):
	job_row.revenue_calculation_method = _row_val(sq_row, "calculation_method") or "Flat Rate"
	job_row.quantity = flt(_row_val(sq_row, "quantity"), 2) or 1
	job_row.uom = _row_val(sq_row, "uom")
	job_row.currency = _row_val(sq_row, "currency")
	job_row.unit_rate = flt(_row_val(sq_row, "unit_rate"), 2)
	job_row.unit_type = _row_val(sq_row, "unit_type")
	job_row.minimum_quantity = flt(_row_val(sq_row, "minimum_quantity"), 2)
	job_row.minimum_charge = flt(_row_val(sq_row, "minimum_charge"), 2)
	job_row.maximum_charge = flt(_row_val(sq_row, "maximum_charge"), 2)
	job_row.base_amount = flt(_row_val(sq_row, "base_amount"), 2)
	job_row.estimated_revenue = flt(_row_val(sq_row, "estimated_revenue"), 2)
	job_row.bill_to = _row_val(sq_row, "bill_to")
	job_row.revenue_calc_notes = _row_val(sq_row, "revenue_calc_notes") or ""
	job_row.description = _row_val(sq_row, "item_name") or job_row.description


def _apply_sq_revenue_to_transport_job_row(job_row, sq_row):
	job_row.revenue_calculation_method = _row_val(sq_row, "calculation_method") or "Flat Rate"
	job_row.quantity = flt(_row_val(sq_row, "quantity"), 2) or 1
	job_row.uom = _row_val(sq_row, "uom")
	job_row.currency = _row_val(sq_row, "currency")
	if hasattr(job_row, "selling_currency"):
		job_row.selling_currency = _row_val(sq_row, "currency")
	job_row.unit_rate = flt(_row_val(sq_row, "unit_rate"), 2)
	job_row.unit_type = _row_val(sq_row, "unit_type")
	job_row.minimum_quantity = flt(_row_val(sq_row, "minimum_quantity"), 2)
	job_row.minimum_charge = flt(_row_val(sq_row, "minimum_charge"), 2)
	job_row.maximum_charge = flt(_row_val(sq_row, "maximum_charge"), 2)
	job_row.base_amount = flt(_row_val(sq_row, "base_amount"), 2)
	job_row.estimated_revenue = flt(_row_val(sq_row, "estimated_revenue"), 2)
	job_row.bill_to = _row_val(sq_row, "bill_to")
	job_row.revenue_calc_notes = _row_val(sq_row, "revenue_calc_notes") or ""
	ic = _row_val(sq_row, "item_code")
	if ic:
		job_row.description = frappe.db.get_value("Item", ic, "item_name") or job_row.description


def _apply_sq_revenue_to_warehouse_job_row(job_row, sq_row):
	job_row.quantity = flt(_row_val(sq_row, "quantity"), 2) or 1
	job_row.uom = _row_val(sq_row, "uom")
	job_row.currency = _row_val(sq_row, "currency")
	job_row.unit_rate = flt(_row_val(sq_row, "unit_rate"), 2)
	job_row.estimated_revenue = flt(_row_val(sq_row, "estimated_revenue"), 2)
	if hasattr(job_row, "bill_to"):
		job_row.bill_to = _row_val(sq_row, "bill_to")


def _apply_sq_revenue_to_sea_job_row(job_row, sq_row):
	job_row.revenue_calculation_method = _row_val(sq_row, "calculation_method") or "Flat Rate"
	job_row.quantity = flt(_row_val(sq_row, "quantity"), 2) or 1
	job_row.uom = _row_val(sq_row, "uom")
	job_row.currency = _row_val(sq_row, "currency")
	if hasattr(job_row, "selling_currency"):
		job_row.selling_currency = _row_val(sq_row, "currency")
	job_row.unit_rate = flt(_row_val(sq_row, "unit_rate"), 2)
	job_row.unit_type = _row_val(sq_row, "unit_type")
	job_row.minimum_quantity = flt(_row_val(sq_row, "minimum_quantity"), 2)
	job_row.minimum_charge = flt(_row_val(sq_row, "minimum_charge"), 2)
	job_row.maximum_charge = flt(_row_val(sq_row, "maximum_charge"), 2)
	job_row.base_amount = flt(_row_val(sq_row, "base_amount"), 2)
	job_row.estimated_revenue = flt(_row_val(sq_row, "estimated_revenue"), 2)
	job_row.bill_to = _row_val(sq_row, "bill_to")
	job_row.revenue_calc_notes = _row_val(sq_row, "revenue_calc_notes") or ""
	ic = _row_val(sq_row, "item_code")
	if ic:
		job_row.description = frappe.db.get_value("Item", ic, "item_name") or job_row.description


def _apply_sq_revenue_to_declaration_job_row(job_row, sq_row):
	job_row.revenue_calculation_method = _row_val(sq_row, "calculation_method") or "Fixed Amount"
	job_row.quantity = flt(_row_val(sq_row, "quantity"), 2) or 1
	job_row.uom = _row_val(sq_row, "uom")
	job_row.currency = _row_val(sq_row, "currency")
	if hasattr(job_row, "selling_currency"):
		job_row.selling_currency = _row_val(sq_row, "currency")
	job_row.unit_rate = flt(_row_val(sq_row, "unit_rate"), 2)
	job_row.unit_type = _row_val(sq_row, "unit_type")
	job_row.minimum_quantity = flt(_row_val(sq_row, "minimum_quantity"), 2)
	job_row.minimum_charge = flt(_row_val(sq_row, "minimum_charge"), 2)
	job_row.maximum_charge = flt(_row_val(sq_row, "maximum_charge"), 2)
	job_row.base_amount = flt(_row_val(sq_row, "base_amount"), 2)
	job_row.estimated_revenue = flt(_row_val(sq_row, "estimated_revenue"), 2)
	job_row.bill_to = _row_val(sq_row, "bill_to")
	job_row.revenue_calc_notes = _row_val(sq_row, "revenue_calc_notes") or ""
	job_row.charge_description = _row_val(sq_row, "item_name") or job_row.charge_description


def _apply_sq_revenue_to_special_project_job_row(job_row, sq_row):
	job_row.revenue_calculation_method = _row_val(sq_row, "calculation_method") or "Flat Rate"
	job_row.quantity = flt(_row_val(sq_row, "quantity"), 2) or 1
	job_row.uom = _row_val(sq_row, "uom")
	job_row.currency = _row_val(sq_row, "currency")
	if hasattr(job_row, "selling_currency"):
		job_row.selling_currency = _row_val(sq_row, "currency")
	job_row.unit_rate = flt(_row_val(sq_row, "unit_rate"), 2)
	job_row.unit_type = _row_val(sq_row, "unit_type")
	job_row.minimum_quantity = flt(_row_val(sq_row, "minimum_quantity"), 2)
	job_row.minimum_charge = flt(_row_val(sq_row, "minimum_charge"), 2)
	job_row.maximum_charge = flt(_row_val(sq_row, "maximum_charge"), 2)
	job_row.base_amount = flt(_row_val(sq_row, "base_amount"), 2)
	job_row.estimated_revenue = flt(_row_val(sq_row, "estimated_revenue"), 2)
	job_row.bill_to = _row_val(sq_row, "bill_to")
	job_row.revenue_calc_notes = _row_val(sq_row, "revenue_calc_notes") or ""
	ic = _row_val(sq_row, "item_code")
	item_name = _row_val(sq_row, "item_name") or ""
	if ic and not item_name:
		item_name = frappe.db.get_value("Item", ic, "item_name") or ""
	if item_name:
		job_row.description = item_name


def _revenue_appliers():
	return {
		"Air Shipment": _apply_sq_revenue_to_air_job_row,
		"Transport Job": _apply_sq_revenue_to_transport_job_row,
		"Warehouse Job": _apply_sq_revenue_to_warehouse_job_row,
		"Sea Shipment": _apply_sq_revenue_to_sea_job_row,
		"Declaration": _apply_sq_revenue_to_declaration_job_row,
		"Declaration Order": _apply_sq_revenue_to_declaration_job_row,
		"Special Project": _apply_sq_revenue_to_special_project_job_row,
	}


def _docs_touched_by_change_request(cr_doc):
	"""Yield every operational doc (Main + satellites) that may carry rows tagged with this CR.

	Resolves the Main from the CR target (directly when target is Main, else via satellite back-link),
	then yields every satellite materialised from an Internal Job that appears either:
	  * on a Change Request Charge row's ``internal_job`` field, or
	  * as the satellite's own ``internal_job`` when the CR was filed against an IJ booking.

	Safe to call from cancel paths — silently skips IJs whose satellite has not been materialised
	yet (the Main row is still cleaned by ``_remove_job_charges_for_change_request``).
	"""
	main_job_type, main_job_name, default_ij = _resolve_main_and_default_internal_job(cr_doc)
	if not main_job_type or not main_job_name:
		return
	try:
		yield frappe.get_doc(main_job_type, main_job_name)
	except frappe.DoesNotExistError:
		return

	ij_names = _linked_service_names_from_cr_doc(cr_doc, default_ij)
	for ij in ij_names:
		sat_type, sat_name = _satellite_for_internal_job(main_job_type, main_job_name, ij)
		if not sat_type or not sat_name:
			continue
		try:
			yield frappe.get_doc(sat_type, sat_name)
		except frappe.DoesNotExistError:
			continue


def link_sales_quote_to_change_request_job_charges(cr_name: str, sales_quote_name: str) -> int:
	"""Set ``sales_quote_link`` on every job/satellite row tagged with this Change Request.

	Walks the Main job AND every Internal Job satellite booking that may have received a mirrored
	cost row at CR submit time, so both sides reference the Sales Quote once it is created.
	"""
	cr_name = (cr_name or "").strip()
	sales_quote_name = (sales_quote_name or "").strip()
	if not cr_name or not sales_quote_name:
		return 0
	if not frappe.db.exists("Change Request", cr_name):
		return 0
	if not frappe.db.exists("Sales Quote", sales_quote_name):
		return 0

	cr_doc = frappe.get_doc("Change Request", cr_name)
	if not getattr(cr_doc, "job_type", None) or not getattr(cr_doc, "job", None):
		return 0

	# CR Charge name -> linked_service tag, used to re-stamp scope on linked job rows.
	cr_charge_ls = _cr_charge_linked_service_map(cr_doc)

	total_updated = 0
	for job_doc in _docs_touched_by_change_request(cr_doc):
		updated_here = 0
		for row in job_doc.get("charges") or []:
			if getattr(row, "change_request", None) != cr_name:
				continue
			crc = (getattr(row, "change_request_charge", None) or "").strip()
			ls = cr_charge_ls.get(crc) or ""
			if ls and _restamp_linked_scope_on_charge_row(row, ls):
				updated_here += 1
			if (getattr(row, "sales_quote_link", None) or "").strip() == sales_quote_name:
				continue
			row.sales_quote_link = sales_quote_name
			updated_here += 1
		if updated_here > 0:
			job_doc.flags.ignore_validate_update_after_submit = True
			job_doc.save(ignore_permissions=True)
			total_updated += updated_here
	return total_updated


def merge_sales_quote_revenue_into_change_request_job_rows(sq_doc):
	"""Update job charge rows tagged with the Sales Quote's Change Request with quote revenue.

	The Sales Quote always points at the Main job (see ``create_sales_quote_from_change_request``);
	this function updates the Main rows in place using the Main-side revenue applier. After updating
	the Main, ``_propagate_sales_quote_revenue_to_change_request_satellites`` mirrors the same
	revenue onto every Internal Job satellite booking that holds a parallel CR-tagged row, so the
	satellite billing reflects the quote outcome too.

	Returns the number of Main rows updated (preserved for backwards compatibility with callers /
	tests). Satellite updates are best-effort and logged via msgprint.
	"""
	cr_name = getattr(sq_doc, "change_request", None)
	if not cr_name:
		return 0
	if not frappe.db.exists("Change Request", cr_name):
		return 0

	job_type = sq_doc.job_type
	applier = _revenue_appliers().get(job_type)
	if not applier:
		return 0

	job_doc = frappe.get_doc(sq_doc.job_type, sq_doc.job)
	cr_doc = frappe.get_doc("Change Request", cr_name)
	cr_charge_ls = _cr_charge_linked_service_map(cr_doc)
	updated = 0
	for sq_row in sq_doc.get("charges") or []:
		if not _row_val(sq_row, "item_code"):
			continue
		ct = _row_val(sq_row, "charge_type") or "Margin"
		if ct in ("Cost",):
			continue
		crc = _row_val(sq_row, "change_request_charge")
		if not crc:
			continue
		job_row = _find_change_request_job_row(job_doc, cr_name, crc)
		if not job_row:
			continue
		applier(job_row, sq_row)
		job_row.sales_quote_link = sq_doc.name
		ls = cr_charge_ls.get(crc) or ""
		if ls:
			_restamp_linked_scope_on_charge_row(job_row, ls)
		updated += 1

	if updated > 0:
		job_doc.flags.ignore_validate_update_after_submit = True
		job_doc.save(ignore_permissions=True)
		frappe.msgprint(
			_("Updated revenue on {0} charge line(s) on {1} from Sales Quote {2}.").format(updated, sq_doc.job, sq_doc.name),
			indicator="green",
		)

	# Mirror the revenue onto satellite mirrored rows when the CR also tagged Internal Jobs.
	# Errors here are non-fatal — the Main side is the source of truth for billing.
	try:
		_propagate_sales_quote_revenue_to_change_request_satellites(sq_doc, cr_name)
	except Exception:
		frappe.log_error(
			title="Change Request satellite revenue propagation failed",
			message=frappe.get_traceback(),
		)
	return updated


def _propagate_sales_quote_revenue_to_change_request_satellites(sq_doc, cr_name):
	"""Mirror quote revenue onto every Internal Job satellite booking row tagged with this CR.

	No-ops gracefully when the Change Request has no IJ-tagged rows or no satellites have been
	materialised. The applier used is the one matching the **satellite's** doctype (e.g. Sea Booking
	uses the Sea applier, Transport Order uses the Transport applier), so revenue fields land in
	the right shape on each child schema.
	"""
	if not cr_name or not frappe.db.exists("Change Request", cr_name):
		return
	cr_doc = frappe.get_doc("Change Request", cr_name)

	# Collect the satellites the CR may have written to.
	main_job_type, main_job_name, default_ij = _resolve_main_and_default_internal_job(cr_doc)
	if not main_job_type or not main_job_name:
		return

	ij_names = _linked_service_names_from_cr_doc(cr_doc, default_ij)
	if not ij_names:
		return

	# Map satellite doctype -> applier (mirrors revenue appliers but keyed by satellite type).
	satellite_appliers = {
		"Transport Order": _apply_sq_revenue_to_transport_job_row,
		"Sea Booking": _apply_sq_revenue_to_sea_job_row,
		"Air Booking": _apply_sq_revenue_to_air_job_row,
		"Declaration Order": _apply_sq_revenue_to_declaration_job_row,
		"Inbound Order": _apply_sq_revenue_to_warehouse_job_row,
		"Release Order": _apply_sq_revenue_to_warehouse_job_row,
	}

	for ij in ij_names:
		sat_type, sat_name = _satellite_for_internal_job(main_job_type, main_job_name, ij)
		if not sat_type or not sat_name:
			continue
		applier = satellite_appliers.get(sat_type)
		if not applier:
			continue
		sat_doc = frappe.get_doc(sat_type, sat_name)
		touched = 0
		for sq_row in sq_doc.get("charges") or []:
			if not _row_val(sq_row, "item_code"):
				continue
			ct = _row_val(sq_row, "charge_type") or "Margin"
			if ct in ("Cost",):
				continue
			crc = _row_val(sq_row, "change_request_charge")
			if not crc:
				continue
			sat_row = _find_change_request_job_row(sat_doc, cr_name, crc)
			if not sat_row:
				continue
			applier(sat_row, sq_row)
			sat_row.sales_quote_link = sq_doc.name
			_restamp_linked_scope_on_charge_row(sat_row, ij)
			touched += 1
		if touched > 0:
			sat_doc.flags.ignore_validate_update_after_submit = True
			sat_doc.save(ignore_permissions=True)


def _zero_revenue_on_job_row(job_row, job_type_for_layout):
	"""Strip quote link + zero revenue fields per the destination job_type's layout."""
	job_row.sales_quote_link = None
	if job_type_for_layout in (
		"Air Shipment",
		"Air Booking",
		"Sea Shipment",
		"Sea Booking",
		"Transport Job",
		"Transport Order",
		"Special Project",
	):
		job_row.estimated_revenue = 0
		if hasattr(job_row, "unit_rate"):
			job_row.unit_rate = 0
		if hasattr(job_row, "revenue_calc_notes"):
			job_row.revenue_calc_notes = ""
	elif job_type_for_layout in ("Warehouse Job", "Inbound Order", "Release Order"):
		if hasattr(job_row, "estimated_revenue"):
			job_row.estimated_revenue = 0
		if hasattr(job_row, "unit_rate"):
			job_row.unit_rate = 0
		if hasattr(job_row, "total"):
			job_row.total = 0
	elif job_type_for_layout in ("Declaration", "Declaration Order"):
		job_row.estimated_revenue = 0
		if hasattr(job_row, "unit_rate"):
			job_row.unit_rate = 0
		if hasattr(job_row, "revenue_calc_notes"):
			job_row.revenue_calc_notes = ""


def clear_sales_quote_revenue_from_change_request_job_rows(sq_doc):
	"""On Sales Quote cancel: strip quote link / revenue from Main rows AND every Internal Job satellite row tagged with this CR + amendment family."""
	cr_name = getattr(sq_doc, "change_request", None)
	if not cr_name:
		return
	if not frappe.db.exists(sq_doc.job_type, sq_doc.job):
		return

	family = _amendment_family_names(sq_doc)
	job_doc = frappe.get_doc(sq_doc.job_type, sq_doc.job)
	job_type = sq_doc.job_type
	changed = False

	for job_row in job_doc.get("charges") or []:
		if getattr(job_row, "change_request", None) != cr_name:
			continue
		link = getattr(job_row, "sales_quote_link", None)
		if not link or link not in family:
			continue
		_zero_revenue_on_job_row(job_row, job_type)
		changed = True

	if changed:
		job_doc.flags.ignore_validate_update_after_submit = True
		job_doc.save(ignore_permissions=True)

	# Best-effort: also walk Internal Job satellites that may have received mirrored revenue.
	try:
		_clear_sales_quote_revenue_from_satellites(sq_doc, cr_name, family)
	except Exception:
		frappe.log_error(
			title="Change Request satellite revenue clear failed",
			message=frappe.get_traceback(),
		)


def _clear_sales_quote_revenue_from_satellites(sq_doc, cr_name, family):
	if not cr_name or not frappe.db.exists("Change Request", cr_name):
		return
	cr_doc = frappe.get_doc("Change Request", cr_name)
	main_job_type, main_job_name, default_ij = _resolve_main_and_default_internal_job(cr_doc)
	if not main_job_type or not main_job_name:
		return
	ij_names = _linked_service_names_from_cr_doc(cr_doc, default_ij)
	for ij in ij_names:
		sat_type, sat_name = _satellite_for_internal_job(main_job_type, main_job_name, ij)
		if not sat_type or not sat_name:
			continue
		sat_doc = frappe.get_doc(sat_type, sat_name)
		changed = False
		for sat_row in sat_doc.get("charges") or []:
			if getattr(sat_row, "change_request", None) != cr_name:
				continue
			link = getattr(sat_row, "sales_quote_link", None)
			if not link or link not in family:
				continue
			_zero_revenue_on_job_row(sat_row, sat_type)
			changed = True
		if changed:
			sat_doc.flags.ignore_validate_update_after_submit = True
			sat_doc.save(ignore_permissions=True)


@frappe.whitelist()
def backfill_internal_job_scope_on_change_request_rows(cr_name: str | None = None) -> dict:
	"""Re-stamp ``charge_scope='Linked'`` and ``linked_service=<X>`` on Change-Request-tagged rows.

	When ``cr_name`` is supplied only that Change Request is fixed; otherwise every submitted
	Change Request is walked. For each CR Charge with a non-empty linked-service value, every
	matching job/satellite row tagged with the CR is patched. Returns a summary dict with the
	count of documents updated.

	Run via::

		bench --site <site> execute logistics.pricing_center.change_request_to_job.backfill_internal_job_scope_on_change_request_rows
	"""
	summary = {"change_requests_processed": 0, "documents_updated": 0, "rows_updated": 0}
	filters = {"docstatus": 1}
	if cr_name:
		filters["name"] = cr_name
	cr_names = [r.name for r in frappe.get_all("Change Request", filters=filters, fields=["name"])]
	for crn in cr_names:
		summary["change_requests_processed"] += 1
		try:
			cr_doc = frappe.get_doc("Change Request", crn)
		except frappe.DoesNotExistError:
			continue
		cr_charge_ls = _cr_charge_linked_service_map(cr_doc)
		if not any(cr_charge_ls.values()):
			continue
		for job_doc in _docs_touched_by_change_request(cr_doc):
			rows_changed = 0
			for row in job_doc.get("charges") or []:
				if getattr(row, "change_request", None) != crn:
					continue
				crc = (getattr(row, "change_request_charge", None) or "").strip()
				ls = cr_charge_ls.get(crc) or ""
				if not ls:
					continue
				if _restamp_linked_scope_on_charge_row(row, ls):
					rows_changed += 1
			if rows_changed > 0:
				job_doc.flags.ignore_validate_update_after_submit = True
				try:
					job_doc.save(ignore_permissions=True)
					summary["documents_updated"] += 1
					summary["rows_updated"] += rows_changed
				except Exception:
					frappe.log_error(
						title="Change Request scope backfill save failed",
						message=frappe.get_traceback(),
					)
	frappe.db.commit()
	return summary
