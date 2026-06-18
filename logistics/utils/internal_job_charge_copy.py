# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Internal jobs: which charge lines apply is determined by the Main Service document's charge
rows whose **service_type** matches this internal job (e.g. Transport on the main job for a
Transport Order internal job). Amounts and rates come from those same main rows (not Sales Quote).
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt

from logistics.utils.charges_calculation import _get_item_code_from_charge
from logistics.utils.charge_service_type import (
	implied_service_type_for_doctype,
	sales_quote_charge_service_types_equal,
)


def should_apply_internal_job_main_charge_overlay(doc):
	if not cint(getattr(doc, "is_internal_job", 0)):
		return False
	mt = getattr(doc, "main_job_type", None)
	mn = getattr(doc, "main_job", None)
	if not mt or not mn or not frappe.db.exists(mt, mn):
		return False
	return True


def _declaration_order_charge_overlay_redundant_with_linked_shipment(doc):
	"""Charges were copied from this freight shipment; overlay would re-clear/re-map the same rows and can zero them."""
	if doc.doctype != "Declaration Order":
		return False
	mt = getattr(doc, "main_job_type", None)
	mn = getattr(doc, "main_job", None) or ""
	if not mn:
		return False
	air = getattr(doc, "air_shipment", None) or ""
	sea = getattr(doc, "sea_shipment", None) or ""
	if mt == "Air Shipment" and air == mn:
		return True
	if mt == "Sea Shipment" and sea == mn:
		return True
	return False


def _main_charge_matches_internal_service(charge, implied_internal, main_doctype):
	"""Main charge row belongs to internal job when service_type matches, or legacy row without service_type matches main doc type."""
	st = cstr(getattr(charge, "service_type", None) or "").strip()
	if st:
		return sales_quote_charge_service_types_equal(st, implied_internal)
	main_implied = implied_service_type_for_doctype(main_doctype)
	return sales_quote_charge_service_types_equal(main_implied, implied_internal)


def _main_job_charge_filter_service_type_for_internal_child(parent_doc):
	"""Which ``service_type`` on the *main* job's charge rows to match when copying onto this internal child.

	Always use the **child** doctype's implied freight service (Sea for Sea Booking, Air for Air
	Booking). The hub may be the opposite mode (e.g. internal Sea under a one-off Air Shipment):
	then the hub document typically has no matching Sea rows, ``populate_internal_job_charges_from_main_service``
	returns zero rows, and Sea Booking charge population falls back to the Sales Quote / one-off quote
	instead of incorrectly consuming the hub's Air lines and skipping Sea.
	"""
	dt = getattr(parent_doc, "doctype", None)
	return implied_service_type_for_doctype(dt)


def _index_main_charges_by_item(main_doc, restrict_service_type=None):
	"""
	Index main job charges by item_code. For internal jobs, only include rows whose service_type
	matches the internal job (avoids wrong row when same item appears under multiple services).
	"""
	by_item = {}
	rows = main_doc.get("charges") or []
	if restrict_service_type:
		rows = [
			ch
			for ch in rows
			if _main_charge_matches_internal_service(ch, restrict_service_type, main_doc.doctype)
		]
	for ch in rows:
		ic = _get_item_code_from_charge(ch)
		if ic and ic not in by_item:
			by_item[ic] = ch
	return by_item


def _iter_main_charge_rows_for_internal_job(parent_doc):
	"""Yield main job charge rows that apply to this internal child.

	When the IJ booking carries a canonical ``internal_job`` link (set by the create / GCFQ flows
	after the per-scope tagging was introduced), only the Main rows tagged ``charge_scope='Internal
	Job'`` with ``internal_job == parent_doc.internal_job`` are returned. This avoids pulling Main
	rows or other IJs' rows into this specific Internal Job booking.

	Legacy Main charges (no ``charge_scope`` column / value) continue to fall back to the previous
	service-type filter so older bookings keep working.
	"""
	if not should_apply_internal_job_main_charge_overlay(parent_doc):
		return
	main = frappe.get_doc(parent_doc.main_job_type, parent_doc.main_job)
	want = _main_job_charge_filter_service_type_for_internal_child(parent_doc)
	if not want:
		return

	ij_link = (getattr(parent_doc, "internal_job", None) or "").strip()
	main_rows = list(main.get("charges") or [])

	# Prefer rows explicitly tagged for this Internal Job, regardless of service type — the per-scope
	# tagging is authoritative. Service type still matters as a sanity check so a mis-tagged row from
	# another mode (e.g. an Air row accidentally tagged onto a Sea IJ) is excluded.
	if ij_link:
		tagged = [
			ch
			for ch in main_rows
			if (cstr(getattr(ch, "internal_job", None) or "").strip() == ij_link)
			and _main_charge_matches_internal_service(ch, want, main.doctype)
		]
		if tagged:
			for ch in tagged:
				yield ch
			return
		# No IJ-tagged rows yet; legacy fall-through to service-type filter below.

	for ch in main_rows:
		# Skip rows tagged for a *different* Internal Job — only Main-scope or matching-scope rows
		# may overlay onto this IJ booking when there are no per-IJ tags for it.
		row_ij = cstr(getattr(ch, "internal_job", None) or "").strip()
		if row_ij and ij_link and row_ij != ij_link:
			continue
		if _main_charge_matches_internal_service(ch, want, main.doctype):
			yield ch


def _revenue_from_main_charge(ch):
	return (
		flt(getattr(ch, "actual_revenue", 0))
		or flt(getattr(ch, "estimated_revenue", 0))
		or flt(getattr(ch, "total_amount", 0))
		or flt(getattr(ch, "selling_amount", 0))
	)


def _cost_from_main_charge(ch):
	return flt(getattr(ch, "actual_cost", 0)) or flt(getattr(ch, "estimated_cost", 0))


_SKIP_AS_DICT_KEYS = frozenset(
	{
		"name",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"docstatus",
		"idx",
		"parent",
		"parentfield",
		"parenttype",
		"doctype",
	}
)


def _scrub_main_row_to_child_dict(main_ch, child_doctype, forced_service_type):
	"""Map a main job charge row into target child table field names."""
	meta = frappe.get_meta(child_doctype)
	valid = {f.fieldname for f in meta.fields}
	raw = main_ch.as_dict() if hasattr(main_ch, "as_dict") else dict(main_ch)
	d = {}
	for k, v in raw.items():
		if k in valid and k not in _SKIP_AS_DICT_KEYS:
			d[k] = v
	if "Transport Order Charges" == child_doctype:
		ur = flt(raw.get("unit_rate"))
		if ur and "unit_rate" in valid:
			d["unit_rate"] = ur
		rm = raw.get("revenue_calculation_method") or raw.get("calculation_method")
		if rm and "revenue_calculation_method" in valid:
			d["revenue_calculation_method"] = rm
	elif "Declaration Order Charges" == child_doctype:
		rt = flt(raw.get("unit_rate"))
		if rt and "unit_rate" in valid:
			d["unit_rate"] = rt
		cb = raw.get("charge_basis") or raw.get("calculation_method") or raw.get("revenue_calculation_method")
		if cb and "charge_basis" in valid:
			d["charge_basis"] = cb
		rm = raw.get("revenue_calculation_method") or raw.get("calculation_method")
		if rm and "revenue_calculation_method" in valid:
			d["revenue_calculation_method"] = rm
	elif "Sea Booking Charges" == child_doctype:
		rt = flt(raw.get("unit_rate"))
		if rt and "unit_rate" in valid:
			d["unit_rate"] = rt
		rm = raw.get("revenue_calculation_method") or raw.get("calculation_method")
		if rm and "revenue_calculation_method" in valid:
			d["revenue_calculation_method"] = rm
	elif "Air Booking Charges" == child_doctype:
		rt = flt(raw.get("unit_rate"))
		if rt and "unit_rate" in valid:
			d["unit_rate"] = rt
		rm = raw.get("revenue_calculation_method") or raw.get("calculation_method")
		if rm and "revenue_calculation_method" in valid:
			d["revenue_calculation_method"] = rm
	if forced_service_type and "service_type" in valid:
		d["service_type"] = forced_service_type
	if "estimated_revenue" in valid:
		d["estimated_revenue"] = _revenue_from_main_charge(main_ch)
	if "estimated_cost" in valid:
		d["estimated_cost"] = _cost_from_main_charge(main_ch)
	ic = _get_item_code_from_charge(main_ch)
	if ic and "item_code" in valid:
		d["item_code"] = ic
	return d if d.get("item_code") else None


def build_internal_job_transport_charge_dicts(parent_doc):
	"""Charge row dicts for Transport Order from main job rows with service_type Transport."""
	out = []
	want = implied_service_type_for_doctype("Transport Order")
	for ch in _iter_main_charge_rows_for_internal_job(parent_doc):
		row = _scrub_main_row_to_child_dict(ch, "Transport Order Charges", want)
		if row:
			out.append(row)
	return out


def build_internal_job_declaration_charge_dicts(parent_doc):
	"""Charge row dicts for Declaration Order from main job rows with service_type Customs."""
	out = []
	want = implied_service_type_for_doctype("Declaration Order")
	for ch in _iter_main_charge_rows_for_internal_job(parent_doc):
		row = _scrub_main_row_to_child_dict(ch, "Declaration Order Charges", want)
		if row:
			out.append(row)
	return out


def build_internal_job_sea_booking_charge_dicts(parent_doc):
	"""Charge row dicts for Sea Booking from main job rows with service_type Sea."""
	out = []
	want = implied_service_type_for_doctype("Sea Booking")
	for ch in _iter_main_charge_rows_for_internal_job(parent_doc):
		row = _scrub_main_row_to_child_dict(ch, "Sea Booking Charges", want)
		if row:
			out.append(row)
	return out


def build_internal_job_air_booking_charge_dicts(parent_doc):
	"""Charge row dicts for Air Booking from main job rows with service_type Air."""
	out = []
	want = implied_service_type_for_doctype("Air Booking")
	for ch in _iter_main_charge_rows_for_internal_job(parent_doc):
		row = _scrub_main_row_to_child_dict(ch, "Air Booking Charges", want)
		if row:
			out.append(row)
	return out


def populate_internal_job_charges_from_main_service(doc):
	"""
	Replace doc.charges from main job (filtered by service_type). Sets overlay flag via apply overlay.
	Returns (count, service_type_label). Unknown doctype returns (0, "").
	"""
	if doc.doctype == "Transport Order":
		dicts = build_internal_job_transport_charge_dicts(doc)
		st_label = _("Transport")
	elif doc.doctype == "Declaration Order":
		dicts = build_internal_job_declaration_charge_dicts(doc)
		st_label = _("Customs")
	elif doc.doctype == "Sea Booking":
		dicts = build_internal_job_sea_booking_charge_dicts(doc)
		st_label = _("Sea")
	elif doc.doctype == "Air Booking":
		dicts = build_internal_job_air_booking_charge_dicts(doc)
		st_label = _("Air")
	else:
		return (0, "")
	doc.set("charges", [])
	for row in dicts:
		doc.append("charges", row)
	apply_internal_job_main_charge_overlay(doc)
	return (len(dicts), st_label)


def _clear_transport_order_charge_amounts(row):
	for fn in (
		"estimated_revenue",
		"estimated_cost",
		"unit_rate",
		"unit_cost",
		"base_amount",
		"cost_base_amount",
		"minimum_charge",
		"maximum_charge",
		"cost_minimum_charge",
		"cost_maximum_charge",
	):
		if hasattr(row, fn):
			setattr(row, fn, 0)
	if hasattr(row, "use_tariff_in_revenue"):
		row.use_tariff_in_revenue = 0
	if hasattr(row, "use_tariff_in_cost"):
		row.use_tariff_in_cost = 0


def _clear_declaration_order_charge_amounts(row):
	for fn in (
		"estimated_revenue",
		"estimated_cost",
		"unit_rate",
		"unit_cost",
		"base_amount",
		"cost_base_amount",
		"minimum_charge",
		"maximum_charge",
	):
		if hasattr(row, fn):
			setattr(row, fn, 0)


def _clear_sea_booking_charge_amounts(row):
	for fn in (
		"estimated_revenue",
		"estimated_cost",
		"unit_rate",
		"unit_cost",
		"base_amount",
		"cost_base_amount",
		"minimum_charge",
		"maximum_charge",
		"cost_minimum_charge",
		"cost_maximum_charge",
	):
		if hasattr(row, fn):
			setattr(row, fn, 0)
	if hasattr(row, "use_tariff_in_revenue"):
		row.use_tariff_in_revenue = 0
	if hasattr(row, "use_tariff_in_cost"):
		row.use_tariff_in_cost = 0


def _clear_air_booking_charge_amounts(row):
	for fn in (
		"estimated_revenue",
		"estimated_cost",
		"unit_rate",
		"unit_cost",
		"base_amount",
		"cost_base_amount",
		"minimum_charge",
		"maximum_charge",
		"cost_minimum_charge",
		"cost_maximum_charge",
	):
		if hasattr(row, fn):
			setattr(row, fn, 0)
	if hasattr(row, "use_tariff_in_revenue"):
		row.use_tariff_in_revenue = 0
	if hasattr(row, "use_tariff_in_cost"):
		row.use_tariff_in_cost = 0


def _apply_main_to_transport_row(row, main_ch):
	rev = _revenue_from_main_charge(main_ch)
	cst = _cost_from_main_charge(main_ch)
	row.estimated_revenue = rev
	row.estimated_cost = cst
	ur = flt(getattr(main_ch, "unit_rate", 0))
	if ur and hasattr(row, "unit_rate"):
		row.unit_rate = ur
	uc = flt(getattr(main_ch, "unit_cost", 0))
	if uc and hasattr(row, "unit_cost"):
		row.unit_cost = uc
	q = getattr(main_ch, "quantity", None)
	if q is not None and hasattr(row, "quantity"):
		row.quantity = flt(q)
	cq = getattr(main_ch, "cost_quantity", None)
	if cq is not None and hasattr(row, "cost_quantity"):
		row.cost_quantity = flt(cq)
	for a, b in (("uom", "uom"), ("currency", "currency"), ("cost_uom", "cost_uom"), ("cost_currency", "cost_currency")):
		if hasattr(main_ch, a) and hasattr(row, b):
			v = getattr(main_ch, a, None)
			if v:
				setattr(row, b, v)
	rn = getattr(main_ch, "revenue_calc_notes", None) or getattr(main_ch, "calculation_notes", None)
	if rn and hasattr(row, "revenue_calc_notes"):
		row.revenue_calc_notes = rn
	cn = getattr(main_ch, "cost_calc_notes", None)
	if cn and hasattr(row, "cost_calc_notes"):
		row.cost_calc_notes = cn


def _apply_main_to_declaration_order_row(row, main_ch):
	rev = _revenue_from_main_charge(main_ch)
	cst = _cost_from_main_charge(main_ch)
	row.estimated_revenue = rev
	row.estimated_cost = cst
	rt = flt(getattr(main_ch, "unit_rate", 0))
	if rt and hasattr(row, "unit_rate"):
		row.unit_rate = rt
	uc = flt(getattr(main_ch, "unit_cost", 0))
	if uc and hasattr(row, "unit_cost"):
		row.unit_cost = uc
	q = getattr(main_ch, "quantity", None)
	if q is not None and hasattr(row, "quantity"):
		row.quantity = flt(q)
	cq = getattr(main_ch, "cost_quantity", None)
	if cq is not None and hasattr(row, "cost_quantity"):
		row.cost_quantity = flt(cq)
	for a, b in (("uom", "uom"), ("currency", "currency")):
		if hasattr(main_ch, a) and hasattr(row, b):
			v = getattr(main_ch, a, None)
			if v:
				setattr(row, b, v)
	rn = getattr(main_ch, "revenue_calc_notes", None)
	if rn and hasattr(row, "revenue_calc_notes"):
		row.revenue_calc_notes = rn
	cn = getattr(main_ch, "cost_calc_notes", None)
	if cn and hasattr(row, "cost_calc_notes"):
		row.cost_calc_notes = cn


def _apply_main_to_sea_booking_row(row, main_ch):
	rev = _revenue_from_main_charge(main_ch)
	cst = _cost_from_main_charge(main_ch)
	row.estimated_revenue = rev
	row.estimated_cost = cst
	rt = flt(getattr(main_ch, "unit_rate", 0))
	if rt and hasattr(row, "unit_rate"):
		row.unit_rate = rt
	uc = flt(getattr(main_ch, "unit_cost", 0))
	if uc and hasattr(row, "unit_cost"):
		row.unit_cost = uc
	q = getattr(main_ch, "quantity", None)
	if q is not None and hasattr(row, "quantity"):
		row.quantity = flt(q)
	cq = getattr(main_ch, "cost_quantity", None)
	if cq is not None and hasattr(row, "cost_quantity"):
		row.cost_quantity = flt(cq)
	for a, b in (("uom", "uom"), ("currency", "currency"), ("cost_uom", "cost_uom"), ("cost_currency", "cost_currency")):
		if hasattr(main_ch, a) and hasattr(row, b):
			v = getattr(main_ch, a, None)
			if v:
				setattr(row, b, v)
	rn = getattr(main_ch, "revenue_calc_notes", None) or getattr(main_ch, "calculation_notes", None)
	if rn and hasattr(row, "revenue_calc_notes"):
		row.revenue_calc_notes = rn
	cn = getattr(main_ch, "cost_calc_notes", None)
	if cn and hasattr(row, "cost_calc_notes"):
		row.cost_calc_notes = cn


def _apply_main_to_air_booking_row(row, main_ch):
	rev = _revenue_from_main_charge(main_ch)
	cst = _cost_from_main_charge(main_ch)
	row.estimated_revenue = rev
	row.estimated_cost = cst
	rt = flt(getattr(main_ch, "unit_rate", 0))
	if rt and hasattr(row, "unit_rate"):
		row.unit_rate = rt
	uc = flt(getattr(main_ch, "unit_cost", 0))
	if uc and hasattr(row, "unit_cost"):
		row.unit_cost = uc
	q = getattr(main_ch, "quantity", None)
	if q is not None and hasattr(row, "quantity"):
		row.quantity = flt(q)
	cq = getattr(main_ch, "cost_quantity", None)
	if cq is not None and hasattr(row, "cost_quantity"):
		row.cost_quantity = flt(cq)
	for a, b in (("uom", "uom"), ("currency", "currency"), ("cost_uom", "cost_uom"), ("cost_currency", "cost_currency")):
		if hasattr(main_ch, a) and hasattr(row, b):
			v = getattr(main_ch, a, None)
			if v:
				setattr(row, b, v)
	rn = getattr(main_ch, "revenue_calc_notes", None) or getattr(main_ch, "calculation_notes", None)
	if rn and hasattr(row, "revenue_calc_notes"):
		row.revenue_calc_notes = rn
	cn = getattr(main_ch, "cost_calc_notes", None)
	if cn and hasattr(row, "cost_calc_notes"):
		row.cost_calc_notes = cn


def apply_internal_job_main_charge_overlay(parent_doc):
	"""
	Sync internal job charge rows from Main Service charge rows (same item_code, same service_type
	scope as this internal job). Sets parent_doc._internal_job_charge_overlay_applied for child validate.
	"""
	if not should_apply_internal_job_main_charge_overlay(parent_doc):
		return
	if _declaration_order_charge_overlay_redundant_with_linked_shipment(parent_doc):
		return
	main = frappe.get_doc(parent_doc.main_job_type, parent_doc.main_job)
	restrict = _main_job_charge_filter_service_type_for_internal_child(parent_doc)
	idx = _index_main_charges_by_item(main, restrict_service_type=restrict)
	dt = parent_doc.doctype
	for row in parent_doc.get("charges") or []:
		if dt == "Transport Order":
			_clear_transport_order_charge_amounts(row)
		elif dt == "Declaration Order":
			_clear_declaration_order_charge_amounts(row)
		elif dt == "Sea Booking":
			_clear_sea_booking_charge_amounts(row)
		elif dt == "Air Booking":
			_clear_air_booking_charge_amounts(row)
		ic = _get_item_code_from_charge(row)
		if not ic or ic not in idx:
			continue
		main_ch = idx[ic]
		if dt == "Transport Order":
			_apply_main_to_transport_row(row, main_ch)
		elif dt == "Declaration Order":
			_apply_main_to_declaration_order_row(row, main_ch)
		elif dt == "Sea Booking":
			_apply_main_to_sea_booking_row(row, main_ch)
		elif dt == "Air Booking":
			_apply_main_to_air_booking_row(row, main_ch)
	parent_doc._internal_job_charge_overlay_applied = True
