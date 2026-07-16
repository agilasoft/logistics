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


def apply_commercial_invoice_totals(doc: Any) -> None:
	"""Persist derived commercial-invoice totals on *doc*."""
	totals = calculate_commercial_invoice_totals(doc)
	for fieldname, value in totals.items():
		doc.set(fieldname, value)


@frappe.whitelist()
def recalculate_commercial_invoice_totals(doc_json: str | dict) -> dict[str, float | str]:
	"""Desk helper: recompute totals from an unsaved parent document payload."""
	doc_dict = json.loads(doc_json) if isinstance(doc_json, str) else doc_json
	return calculate_commercial_invoice_totals(doc_dict)
