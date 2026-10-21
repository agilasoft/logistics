# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
# For license information, please see license.txt

"""Derive commercial-invoice totals from line items and invoice charges.

Financial totals (invoice total, FOB, CIF, balance) and Invoice Details
measurements (volume, gross weight, net weight, packages) come from the
commercial invoice line items.
"""

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, flt, today

DEDUCTION_CHARGE_CODES = frozenset({"DIS", "DED"})


def _row_value(row: Any, fieldname: str, default=None):
	if isinstance(row, dict):
		return row.get(fieldname, default)
	return getattr(row, fieldname, default)


def _normalize_charge_code(code: str | None) -> str:
	return (code or "").strip().upper()


def _charge_row_amount_in_inv_currency(row: Any, inv_currency: str, posting_date: str | None) -> float:
	amount = flt(_row_value(row, "amount"))
	if not amount:
		return 0.0

	row_currency = (_row_value(row, "currency") or inv_currency or "").strip()
	inv_currency = (inv_currency or "").strip()
	if not row_currency or not inv_currency or row_currency == inv_currency:
		return amount

	from erpnext.setup.utils import get_exchange_rate

	rate = flt(get_exchange_rate(row_currency, inv_currency, posting_date or today(), "for_selling"))
	return amount * rate if rate else amount


def positive_invoice_qty(row: Any) -> float:
	"""Invoice qty when greater than 0, otherwise customs qty when that is greater than 0.

	A qty of 0 is not treated as missing, so it is not replaced by 1.
	"""
	invoice_qty = flt(_row_value(row, "invoice_qty"))
	if invoice_qty > 0:
		return invoice_qty
	customs_qty = flt(_row_value(row, "customs_qty"))
	if customs_qty > 0:
		return customs_qty
	return 0.0


def invoice_qty_is_explicit_zero(row: Any) -> bool:
	"""True when invoice qty was set to 0. Blank (None or empty) stays allowed."""
	if isinstance(row, dict):
		if "invoice_qty" not in row:
			return False
		raw = row.get("invoice_qty")
	else:
		raw = _row_value(row, "invoice_qty", None)
		if raw is None and hasattr(row, "__dict__") and "invoice_qty" not in row.__dict__:
			return False
	if raw is None or (isinstance(raw, str) and not raw.strip()):
		return False
	return flt(raw) == 0


def throw_if_invoice_qty_is_zero(doc: Any) -> None:
	"""Reject a commercial invoice line whose invoice qty is 0."""
	rows = doc.get("commercial_invoice_line_items") if hasattr(doc, "get") else None
	if rows is None:
		rows = getattr(doc, "commercial_invoice_line_items", None) or []
	for idx, row in enumerate(rows or [], start=1):
		if invoice_qty_is_explicit_zero(row):
			frappe.throw(
				_("Row {0}: Invoice Qty must be greater than 0.").format(idx),
				title=_("Invalid Invoice Qty"),
			)


_MEASUREMENT_SPECS = (
	# line value, line uom, header value, header uom, measurement kind
	("volume", "volume_uom", "inv_volume", "inv_volume_uom", "volume"),
	("gross_weight", "gross_weight_uom", "inv_gross_weight", "inv_gross_weight_uom", "weight"),
	("net_weight", "net_weight_uom", "inv_net_weight", "inv_net_weight_uom", "weight"),
)


def _line_rows(doc: Any) -> list:
	if isinstance(doc, dict):
		rows = doc.get("commercial_invoice_line_items") or []
	else:
		rows = getattr(doc, "commercial_invoice_line_items", None)
		if rows is None and hasattr(doc, "get"):
			rows = doc.get("commercial_invoice_line_items") or []
	return list(rows or [])


def _distinct_positive_uoms(rows: list, value_field: str, uom_field: str) -> list[str]:
	seen: list[str] = []
	seen_keys: set[str] = set()
	for row in rows:
		if flt(_row_value(row, value_field)) <= 0:
			continue
		uom = str(_row_value(row, uom_field) or "").strip()
		key = uom.upper()
		if uom and key not in seen_keys:
			seen_keys.add(key)
			seen.append(uom)
	return seen


def _default_measure_uom(kind: str, company: str | None) -> str:
	try:
		from logistics.utils.default_uom import measurement_default_uom

		if kind == "volume":
			return measurement_default_uom("aggregation_volume", company=company) or ""
		return measurement_default_uom("weight", company=company) or ""
	except Exception:
		return ""


def _target_measure_uom(
	doc: Any,
	rows: list,
	value_field: str,
	uom_field: str,
	header_uom_field: str,
	kind: str,
) -> tuple[str, list[str]]:
	"""Pick the Invoice Details unit for a measurement.

	When every contributing line uses the same unit, follow that unit.
	Mixed units convert into the header unit when one is already set,
	otherwise into the logistics default for that measurement.
	"""
	explicit = _distinct_positive_uoms(rows, value_field, uom_field)
	header = str(_row_value(doc, header_uom_field) or "").strip()
	if len(explicit) == 1:
		return explicit[0], explicit
	if len(explicit) > 1:
		return (header or _default_measure_uom(kind, _row_value(doc, "company")) or explicit[0]), explicit
	return header, explicit


def _sum_line_measure(
	doc: Any,
	rows: list,
	value_field: str,
	uom_field: str,
	header_value_field: str,
	header_uom_field: str,
	kind: str,
) -> dict[str, float | str]:
	if not any(flt(_row_value(row, value_field)) > 0 for row in rows):
		return {}

	target, explicit = _target_measure_uom(doc, rows, value_field, uom_field, header_uom_field, kind)
	company = _row_value(doc, "company")
	if kind == "volume":
		from logistics.utils.measurements import convert_volume as convert
	else:
		from logistics.utils.measurements import convert_weight as convert

	target_key = (target or "").strip().upper()
	total = 0.0
	for row in rows:
		value = flt(_row_value(row, value_field))
		if value <= 0:
			continue
		from_uom = str(_row_value(row, uom_field) or "").strip() or target
		if not target or not from_uom or from_uom.strip().upper() == target_key:
			total += value
			continue
		total += flt(convert(value, from_uom=from_uom, to_uom=target, company=company))

	totals: dict[str, float | str] = {header_value_field: total}
	if explicit and target:
		totals[header_uom_field] = target
	return totals


def _packages_from_lines(rows: list) -> dict[str, float | str]:
	total = 0.0
	used = False
	types: list[str] = []
	for row in rows:
		packs = flt(_row_value(row, "no_of_packs"))
		if packs <= 0:
			continue
		used = True
		total += packs
		package_type = str(_row_value(row, "package_type") or "").strip()
		if package_type and package_type not in types:
			types.append(package_type)
	if not used:
		return {}

	totals: dict[str, float | str] = {"packages": total}
	if len(types) == 1 and frappe.db.exists("UOM", types[0]):
		totals["packages_uom"] = types[0]
	return totals


def calculate_invoice_detail_measures(doc: Any) -> dict[str, float | str]:
	"""Total Invoice Details volume, weight, and packages from line items.

	A header value is left unchanged when no line carries that measurement,
	so a summary entered on the header still stands.
	"""
	rows = _line_rows(doc)
	if not rows:
		return {}

	totals: dict[str, float | str] = {}
	for value_field, uom_field, header_value, header_uom, kind in _MEASUREMENT_SPECS:
		totals.update(
			_sum_line_measure(doc, rows, value_field, uom_field, header_value, header_uom, kind)
		)
	totals.update(_packages_from_lines(rows))
	return totals


def calculate_expected_invoice_line_total(doc: Any) -> float:
	total = 0.0
	for row in doc.get("commercial_invoice_line_items") or []:
		qty = positive_invoice_qty(row)
		price = flt(_row_value(row, "price"))
		total += qty * price
	return total


def calculate_commercial_invoice_totals(doc: Any) -> dict[str, float | str]:
	"""Return commercial-invoice totals, including Invoice Details measured from line items."""
	inv_currency = (_row_value(doc, "inv_currency") if not isinstance(doc, dict) else doc.get("inv_currency")) or ""
	posting_date = (
		_row_value(doc, "inv_date") if not isinstance(doc, dict) else doc.get("inv_date")
	) or today()

	line_total = calculate_expected_invoice_line_total(doc)
	fob_additions = 0.0
	post_fob_additions = 0.0
	deductions = 0.0
	charges_for_itot = 0.0
	charges_excl_from_itot = cint(
		_row_value(doc, "charges_excl_from_itot") if not isinstance(doc, dict) else doc.get("charges_excl_from_itot")
	)

	for row in doc.get("commercial_invoice_charges") or []:
		included_in_inv_amt = cint(_row_value(row, "included_in_inv_amt"))
		amount = _charge_row_amount_in_inv_currency(row, inv_currency, posting_date)
		if not amount:
			continue

		if not included_in_inv_amt and not charges_excl_from_itot:
			charges_for_itot += amount

		if included_in_inv_amt:
			continue

		code = _normalize_charge_code(_row_value(row, "charge_code"))
		if code in DEDUCTION_CHARGE_CODES:
			deductions += amount
		elif cint(_row_value(row, "add_to_fob")):
			fob_additions += amount
		else:
			post_fob_additions += amount

	has_lines = invoice_line_row_count(doc) > 0
	typed_inv_total = flt(
		_row_value(doc, "inv_total_amount") if not isinstance(doc, dict) else doc.get("inv_total_amount")
	)
	inv_total = line_total if has_lines else typed_inv_total

	if line_total:
		base = line_total
	else:
		base = inv_total

	fob = max(base + fob_additions - deductions, 0)
	cif = max(fob + post_fob_additions, 0)

	if inv_total:
		allocated = line_total + charges_for_itot
		balance = f"{inv_total - allocated:.2f}"
	else:
		balance = ""

	totals: dict[str, float | str] = {
		"expected_invoice_line_total": line_total,
		"fob": fob,
		"cif": cif,
		"balance": balance,
	}
	if has_lines:
		totals["inv_total_amount"] = line_total
	totals.update(calculate_invoice_detail_measures(doc))
	return totals


def invoice_line_row_count(doc: Any) -> int:
	"""Number of commercial invoice line rows on *doc*."""
	if isinstance(doc, dict):
		rows = doc.get("commercial_invoice_line_items") or []
	else:
		rows = getattr(doc, "commercial_invoice_line_items", None) or []
		if not rows and hasattr(doc, "get"):
			rows = doc.get("commercial_invoice_line_items") or []
	return len(rows or [])


def _charge_item_count_qty(charge: Any) -> float:
	ut = (_row_value(charge, "unit_type") or "").strip()
	cut = (_row_value(charge, "cost_unit_type") or "").strip()
	qty = 0.0
	if ut == "Item Count":
		qty = max(qty, flt(_row_value(charge, "quantity") or 0))
	if cut == "Item Count":
		qty = max(qty, flt(_row_value(charge, "cost_quantity") or 0))
	return qty


def seed_number_of_line_items_from_item_count_charges(doc: Any) -> None:
	"""If the header is empty, copy Item Count charge qty from the quote/charges grid.

	Marks the value as manual so a later 1-row summary does not reset a quoted line count
	(for example quote qty 100). If the user later adds more invoice rows than the header,
	``sync_number_of_line_items`` raises the header to the row count.
	"""
	if isinstance(doc, dict):
		current = cint(doc.get("number_of_line_items") or 0)
	else:
		current = cint(getattr(doc, "number_of_line_items", None) or 0)
	if current > 0:
		return

	qty = 0.0
	if isinstance(doc, dict):
		charges = doc.get("charges") or []
	elif hasattr(doc, "get"):
		charges = doc.get("charges") or getattr(doc, "charges", None) or []
	else:
		charges = getattr(doc, "charges", None) or []
	for charge in charges or []:
		qty = max(qty, _charge_item_count_qty(charge))
	qty_i = cint(qty)
	if qty_i <= 0:
		return
	if isinstance(doc, dict):
		doc["number_of_line_items"] = qty_i
		doc["number_of_line_items_manual"] = 1
	else:
		doc.number_of_line_items = qty_i
		doc.number_of_line_items_manual = 1


def sync_number_of_line_items(doc: Any) -> None:
	"""Default Number of Line Items from row count without wiping a user override.

	Auto-fill when empty or not manual. Keep a manual value (for example 100 with 1 row)
	unless the invoice table grows past that number, in which case follow the rows.
	"""
	row_count = invoice_line_row_count(doc)
	if isinstance(doc, dict):
		current = cint(doc.get("number_of_line_items") or 0)
		manual = cint(doc.get("number_of_line_items_manual") or 0)
	else:
		current = cint(getattr(doc, "number_of_line_items", None) or 0)
		manual = cint(getattr(doc, "number_of_line_items_manual", None) or 0)

	if manual:
		if row_count > current:
			if isinstance(doc, dict):
				doc["number_of_line_items"] = row_count
				doc["number_of_line_items_manual"] = 0
			else:
				doc.number_of_line_items = row_count
				doc.number_of_line_items_manual = 0
		return

	if row_count > 0:
		if isinstance(doc, dict):
			doc["number_of_line_items"] = row_count
		else:
			doc.number_of_line_items = row_count


def apply_number_of_line_items_user_edit(doc: Any) -> None:
	"""Set or clear the manual flag from a user-typed header value."""
	row_count = invoice_line_row_count(doc)
	if isinstance(doc, dict):
		value = cint(doc.get("number_of_line_items") or 0)
		doc["number_of_line_items_manual"] = 0 if value == row_count else 1
	else:
		value = cint(getattr(doc, "number_of_line_items", None) or 0)
		doc.number_of_line_items_manual = 0 if value == row_count else 1


def apply_commercial_invoice_totals(doc: Any) -> None:
	"""Persist derived commercial-invoice totals on *doc*."""
	totals = calculate_commercial_invoice_totals(doc)
	for fieldname, value in totals.items():
		doc.set(fieldname, value)
	seed_number_of_line_items_from_item_count_charges(doc)
	sync_number_of_line_items(doc)


@frappe.whitelist()
def recalculate_commercial_invoice_totals(doc_json: str | dict) -> dict[str, float | str]:
	"""Desk helper: recompute totals from an unsaved parent document payload."""
	doc_dict = json.loads(doc_json) if isinstance(doc_json, str) else doc_json
	return calculate_commercial_invoice_totals(doc_dict)
