# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
# For license information, please see license.txt

"""Derive commercial-invoice financial totals from line items and invoice charges."""

from __future__ import annotations

import json
from typing import Any

import frappe
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


def calculate_expected_invoice_line_total(doc: Any) -> float:
	total = 0.0
	for row in doc.get("commercial_invoice_line_items") or []:
		qty = flt(_row_value(row, "invoice_qty") or _row_value(row, "customs_qty") or 1)
		price = flt(_row_value(row, "price"))
		total += qty * price
	return total


def calculate_commercial_invoice_totals(doc: Any) -> dict[str, float | str]:
	"""Return CIF, FOB, expected line total, and ITOT balance from invoice data."""
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

	if line_total:
		base = line_total
	else:
		base = flt(_row_value(doc, "inv_total_amount") if not isinstance(doc, dict) else doc.get("inv_total_amount"))

	fob = max(base + fob_additions - deductions, 0)
	cif = max(fob + post_fob_additions, 0)

	inv_total = flt(_row_value(doc, "inv_total_amount") if not isinstance(doc, dict) else doc.get("inv_total_amount"))
	if inv_total:
		allocated = line_total + charges_for_itot
		balance = f"{inv_total - allocated:.2f}"
	else:
		balance = ""

	return {
		"expected_invoice_line_total": line_total,
		"fob": fob,
		"cif": cif,
		"balance": balance,
	}


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
