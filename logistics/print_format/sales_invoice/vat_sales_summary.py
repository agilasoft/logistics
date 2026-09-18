# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Sales Invoice print: Vatable / Exempt / Zero-rated totals from the tax template."""

from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import flt

VATABLE = "vatable"
EXEMPT = "exempt"
ZERO_RATED = "zero_rated"


def get_vat_sales_summary(doc) -> frappe._dict:
	"""Classify invoice net sales from Sales Taxes and Charges (template) + Tax Category.

	Returns transaction-currency amounts for the Sales Invoice HTML VAT block.
	"""
	net_total = flt(getattr(doc, "net_total", None) or 0)
	rows = _classified_tax_rows(doc)
	treatments = {treatment for treatment, _amount in rows}

	if len(treatments) == 1:
		buckets = _empty_buckets()
		buckets[next(iter(treatments))] = net_total
	elif len(treatments) > 1:
		if any(amount for _treatment, amount in rows):
			buckets = _empty_buckets()
			for treatment, amount in rows:
				buckets[treatment] += amount
		else:
			buckets = _buckets_from_items(doc)
			if not _has_amounts(buckets):
				buckets[VATABLE] = net_total
	else:
		treatment = _category_treatment(doc)
		buckets = _empty_buckets()
		if treatment:
			buckets[treatment] = net_total
		else:
			buckets = _buckets_from_items(doc)
			if not _has_amounts(buckets):
				buckets[VATABLE] = net_total

	return frappe._dict(
		vatable_sales=buckets[VATABLE],
		exempt_sales=buckets[EXEMPT],
		zero_rated_sales=buckets[ZERO_RATED],
		total_sales=buckets[VATABLE] + buckets[EXEMPT] + buckets[ZERO_RATED],
	)


def _empty_buckets() -> dict[str, float]:
	return {VATABLE: 0.0, EXEMPT: 0.0, ZERO_RATED: 0.0}


def _has_amounts(buckets: dict[str, float]) -> bool:
	return bool(buckets[VATABLE] or buckets[EXEMPT] or buckets[ZERO_RATED])


def _classified_tax_rows(doc) -> list[tuple[str, float]]:
	rows: list[tuple[str, float]] = []
	for tax in getattr(doc, "taxes", None) or []:
		label = _tax_label(tax)
		if _is_withholding(tax, label):
			continue
		treatment = _classify_text(label)
		if not treatment:
			continue
		rows.append((treatment, flt(_row_value(tax, "net_amount"))))
	return rows


def _category_treatment(doc) -> str | None:
	candidates: list[str] = []
	tax_category = _row_value(doc, "tax_category")
	if tax_category:
		candidates.append(str(tax_category))
	template_name = _row_value(doc, "taxes_and_charges")
	if template_name:
		candidates.extend(_template_hints(str(template_name)))
	for candidate in candidates:
		treatment = _classify_text(candidate)
		if treatment:
			return treatment
	return None


def _template_hints(template_name: str) -> list[str]:
	hints = [template_name]
	try:
		row = frappe.db.get_value(
			"Sales Taxes and Charges Template",
			template_name,
			["tax_category", "title"],
			as_dict=True,
		)
	except Exception:
		return hints
	if not row:
		return hints
	for key in ("tax_category", "title"):
		value = row.get(key) if isinstance(row, dict) else getattr(row, key, None)
		if value:
			hints.append(str(value))
	return hints


def _buckets_from_items(doc) -> dict[str, float]:
	buckets = _empty_buckets()
	for item in getattr(doc, "items", None) or []:
		item_net = flt(_row_value(item, "net_amount") or _row_value(item, "amount"))
		item_treatment = str(_row_value(item, "vat_treatment") or "").lower()
		item_template = str(_row_value(item, "item_tax_template") or "").lower()
		if (
			"zero rated" in item_treatment
			or "zero-rated" in item_treatment
			or "zero rated" in item_template
			or "zero-rated" in item_template
		):
			buckets[ZERO_RATED] += item_net
		elif "exempt" in item_treatment or ("exempt" in item_template and "zero" not in item_template):
			buckets[EXEMPT] += item_net
		else:
			buckets[VATABLE] += item_net
	return buckets


def _tax_label(tax) -> str:
	parts: list[str] = []
	account_head = str(_row_value(tax, "account_head") or "")
	if account_head:
		parts.append(account_head)
		account_name = _account_name(account_head)
		if account_name:
			parts.append(account_name)
	description = str(_row_value(tax, "description") or "")
	if description:
		parts.append(description)
	return " ".join(parts).lower()


def _account_name(account_head: str) -> str:
	try:
		return str(frappe.db.get_value("Account", account_head, "account_name") or "")
	except Exception:
		return ""


def _is_withholding(tax, label: str) -> bool:
	if _row_value(tax, "is_withholding_tax"):
		return True
	if _row_value(tax, "is_tax_withholding_account"):
		return True
	return "withhold" in (label or "")


def _classify_text(text: str | None) -> str | None:
	label = (text or "").lower()
	if not label.strip() or "withhold" in label:
		return None
	if "zero rated" in label or "zero-rated" in label:
		return ZERO_RATED
	if "exempt" in label:
		return EXEMPT
	if "vatable" in label or "vat" in label:
		return VATABLE
	return None


def _row_value(row, key: str) -> Any:
	if row is None:
		return None
	if isinstance(row, dict):
		return row.get(key)
	if hasattr(row, "get"):
		try:
			return row.get(key)
		except Exception:
			pass
	return getattr(row, key, None)
