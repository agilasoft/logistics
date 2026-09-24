# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Disbursement Bill print: SI lines whose source Charge Type is Disbursement."""

from __future__ import annotations

from typing import Any, List, Sequence, Tuple

import frappe
from frappe.utils import flt

from logistics.invoice_integration.sales_invoice_api import SALES_CHARGES_CHILD_DOCTYPE

_QTY_TOLERANCE = 0.0001


def get_disbursement_line_items(doc) -> List[Any]:
	"""Return Sales Invoice items that correspond to Disbursement charges."""
	items = list(doc.items or [])
	if not items:
		return []

	keys = _collect_disbursement_charge_keys(doc.name)
	if keys:
		return _match_items_to_charge_keys(items, keys)

	return [item for item in items if _item_default_is_disbursement(getattr(item, "item_code", None))]


def get_non_disbursement_line_items(doc) -> List[Any]:
	"""Return Sales Invoice items that are not Disbursement charges.

	Complement of get_disbursement_line_items so a line prints on the service
	invoice or the disbursement bill, not both.
	"""
	items = list(doc.items or [])
	if not items:
		return []
	excluded = {id(item) for item in get_disbursement_line_items(doc)}
	return [item for item in items if id(item) not in excluded]


def get_taxable_freight_line_items(doc) -> List[Any]:
	"""Return the 5% Sales Invoice rows created from Taxable Freight Item."""
	items = list(doc.items or [])
	if not items:
		return []
	keys = _collect_taxable_freight_item_keys(getattr(doc, "name", None))
	if not keys:
		return []
	return _match_items_to_charge_keys(items, keys)


def get_freight_95_main_line_items(doc) -> List[Any]:
	"""Return the 95% Sales Invoice rows for charges with Apply 95/5 rule checked."""
	items = list(doc.items or [])
	if not items:
		return []
	keys = _collect_freight_95_main_item_keys(getattr(doc, "name", None))
	if not keys:
		return []
	return _match_items_to_charge_keys(items, keys)


def get_sales_invoice_print_items(doc) -> List[Any]:
	"""Service-invoice rows: omit Disbursement charges and the 95% freight line.

	The 5% Taxable Freight Item line stays on this print.
	"""
	items = get_non_disbursement_line_items(doc)
	if not items:
		return []
	excluded = {id(item) for item in get_freight_95_main_line_items(doc)}
	return [item for item in items if id(item) not in excluded]


def _disbursement_bill_line_items(doc) -> List[Any]:
	"""Disbursement charges and the 95% freight line, in document order."""
	items = list(doc.items or [])
	if not items:
		return []
	included = {id(item) for item in get_disbursement_line_items(doc)}
	included.update(id(item) for item in get_freight_95_main_line_items(doc))
	return [item for item in items if id(item) in included]


def get_disbursement_bill_context(doc) -> frappe._dict:
	"""Items plus totals for the Disbursement Bill print format."""
	items = _disbursement_bill_line_items(doc)
	total = sum(flt(getattr(item, "net_amount", 0)) for item in items)
	all_shown = bool(doc.items) and len(items) == len(doc.items)
	discount = flt(getattr(doc, "discount_amount", 0) or 0) if all_shown else 0.0
	return frappe._dict(
		line_items=items,
		total=total,
		discount_amount=discount,
		total_amount_due=total - discount,
		all_items_shown=all_shown,
	)


def _collect_disbursement_charge_keys(si_name: str) -> List[Tuple[str, float]]:
	keys: List[Tuple[str, float]] = []
	for dt in SALES_CHARGES_CHILD_DOCTYPE.values():
		if not frappe.db.exists("DocType", dt):
			continue
		if not frappe.db.table_exists(dt):
			continue
		meta = frappe.get_meta(dt)
		if not meta.get_field("sales_invoice") or not meta.get_field("charge_type"):
			continue
		item_field = "item_code" if meta.get_field("item_code") else None
		if not item_field and meta.get_field("charge_item"):
			item_field = "charge_item"
		if not item_field:
			continue
		qty_field = "quantity" if meta.get_field("quantity") else None
		fields = [item_field]
		if qty_field:
			fields.append(qty_field)
		rows = frappe.get_all(
			dt,
			filters={"sales_invoice": si_name, "charge_type": "Disbursement"},
			fields=fields,
		)
		for row in rows:
			code = row.get(item_field)
			if not code:
				continue
			qty = flt(row.get(qty_field)) if qty_field else 0.0
			keys.append((code, qty))
	return keys


def _collect_freight_95_main_item_keys(si_name: str | None) -> List[Tuple[str, float]]:
	"""One (charge item, qty 1) key per 95/5 charge. The split always posts the 95% row at qty 1."""
	if not si_name:
		return []
	keys: List[Tuple[str, float]] = []
	for dt in SALES_CHARGES_CHILD_DOCTYPE.values():
		if not frappe.db.exists("DocType", dt):
			continue
		if not frappe.db.table_exists(dt):
			continue
		meta = frappe.get_meta(dt)
		if not meta.get_field("sales_invoice") or not meta.get_field("apply_95_5_rule"):
			continue
		item_field = "item_code" if meta.get_field("item_code") else None
		if not item_field and meta.get_field("charge_item"):
			item_field = "charge_item"
		if not item_field:
			continue
		rows = frappe.get_all(
			dt,
			filters={"sales_invoice": si_name, "apply_95_5_rule": 1},
			fields=[item_field],
		)
		for row in rows:
			code = row.get(item_field)
			if not code:
				continue
			keys.append((code, 1.0))
	return keys


def _collect_taxable_freight_item_keys(si_name: str | None) -> List[Tuple[str, float]]:
	"""One (item, qty 1) key per 95/5 charge. The split always posts the 5% row at qty 1."""
	if not si_name:
		return []
	keys: List[Tuple[str, float]] = []
	for dt in SALES_CHARGES_CHILD_DOCTYPE.values():
		if not frappe.db.exists("DocType", dt):
			continue
		if not frappe.db.table_exists(dt):
			continue
		meta = frappe.get_meta(dt)
		if (
			not meta.get_field("sales_invoice")
			or not meta.get_field("taxable_freight_item")
			or not meta.get_field("apply_95_5_rule")
		):
			continue
		rows = frappe.get_all(
			dt,
			filters={"sales_invoice": si_name, "apply_95_5_rule": 1},
			fields=["taxable_freight_item"],
		)
		for row in rows:
			code = row.get("taxable_freight_item")
			if not code:
				continue
			keys.append((code, 1.0))
	return keys


def _match_items_to_charge_keys(items: Sequence[Any], keys: List[Tuple[str, float]]) -> List[Any]:
	remaining = list(keys)
	matched: List[Any] = []
	for item in items:
		code = getattr(item, "item_code", None)
		if not code:
			continue
		qty = flt(getattr(item, "qty", 0))
		match_idx = None
		for i, (charge_code, charge_qty) in enumerate(remaining):
			if charge_code == code and abs(charge_qty - qty) <= _QTY_TOLERANCE:
				match_idx = i
				break
		if match_idx is None:
			continue
		remaining.pop(match_idx)
		matched.append(item)
	return matched


def _item_default_is_disbursement(item_code: str | None) -> bool:
	if not item_code:
		return False
	charge_type = (frappe.db.get_value("Item", item_code, "custom_default_charge_type") or "").strip()
	return charge_type.lower() == "disbursement"
