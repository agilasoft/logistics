# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Sales Invoice print: Vatable / Exempt / Zero-rated totals from the tax template."""

from __future__ import annotations

import json
import re
from typing import Any

import frappe
from frappe.utils import flt

VATABLE = "vatable"
EXEMPT = "exempt"
ZERO_RATED = "zero_rated"


def get_vat_sales_summary(doc, items=None) -> frappe._dict:
	"""Classify invoice net sales from Sales Taxes and Charges (template) + Tax Category.

	Returns transaction-currency amounts for the Sales Invoice HTML VAT block.
	When any charge line has an Item Tax Template or item_tax_rate, split by
	the printed Amount column (net − tax) using those rates
	(VAT Exempt / Zero Rated / Vatable).
	Pass `items` to classify a subset (e.g. Disbursement Bill lines) instead of
	the full invoice; `net_total` is then the sum of those lines.
	"""
	print_items = list(items) if items is not None else None
	if print_items is not None:
		net_total = sum(
			flt(_row_value(item, "net_amount") or _row_value(item, "amount"))
			for item in print_items
		)
	else:
		net_total = flt(getattr(doc, "net_total", None) or 0)
	rows = _classified_tax_rows(doc)
	treatments = {treatment for treatment, _amount in rows}

	if _has_item_tax_templates(doc, items=print_items):
		default = _default_item_treatment(treatments, doc)
		buckets = _buckets_from_items(doc, default_treatment=default, items=print_items)
		if not _has_amounts(buckets):
			buckets[default] = net_total
	elif len(treatments) == 1:
		buckets = _empty_buckets()
		buckets[next(iter(treatments))] = net_total
	elif len(treatments) > 1:
		if print_items is not None:
			buckets = _buckets_from_items(doc, items=print_items)
			if not _has_amounts(buckets):
				buckets[VATABLE] = net_total
		elif any(amount for _treatment, amount in rows):
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
			buckets = _buckets_from_items(doc, items=print_items)
			if not _has_amounts(buckets):
				buckets[VATABLE] = net_total

	return frappe._dict(
		vatable_sales=buckets[VATABLE],
		exempt_sales=buckets[EXEMPT],
		zero_rated_sales=buckets[ZERO_RATED],
		total_sales=buckets[VATABLE] + buckets[EXEMPT] + buckets[ZERO_RATED],
	)


def item_is_zero_rated_or_exempt(doc, item) -> bool:
	"""True when a printed charge line is Zero Rated or VAT Exempt (not merely 0.00 tax)."""
	return _item_vat_treatment(doc, item) in (ZERO_RATED, EXEMPT)


def _item_vat_treatment(doc, item) -> str:
	return _item_treatment(item, _invoice_default_treatment(doc), {})


def _invoice_default_treatment(doc) -> str:
	rows = _classified_tax_rows(doc)
	treatments = {treatment for treatment, _amount in rows}
	if _has_item_tax_templates(doc):
		return _default_item_treatment(treatments, doc)
	if len(treatments) == 1:
		return next(iter(treatments))
	if len(treatments) > 1:
		return VATABLE
	return _category_treatment(doc) or VATABLE


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


def _has_item_tax_templates(doc, items=None) -> bool:
	for item in (items if items is not None else getattr(doc, "items", None)) or []:
		if _row_value(item, "item_tax_template") or _parse_item_tax_rate(_row_value(item, "item_tax_rate")):
			return True
	return False


def _default_item_treatment(treatments: set[str], doc) -> str:
	if len(treatments) == 1:
		return next(iter(treatments))
	if not treatments:
		return _category_treatment(doc) or VATABLE
	return VATABLE


def _doc_vat_rate(doc) -> float:
	rate = 0.0
	for tax in getattr(doc, "taxes", None) or []:
		label = _tax_label(tax)
		if _is_withholding(tax, label):
			continue
		tax_rate = flt(_row_value(tax, "rate"))
		if tax_rate <= 0:
			continue
		if _classify_text(label) == VATABLE:
			rate += tax_rate
	return rate


def _print_line_tax(item, net: float, vat_rate: float) -> float:
	if _row_value(item, "item_tax_template"):
		custom = _row_value(item, "custom_tax_amount")
		if custom is not None:
			return flt(custom)
		tax_amount = _row_value(item, "tax_amount")
		return flt(tax_amount) if tax_amount is not None else 0.0
	return flt(net) * (flt(vat_rate) / 100)


def _print_line_amount(item, vat_rate: float) -> float:
	net = flt(_row_value(item, "net_amount") or _row_value(item, "amount"))
	return net - _print_line_tax(item, net, vat_rate)


def _buckets_from_items(doc, default_treatment: str = VATABLE, items=None) -> dict[str, float]:
	buckets = _empty_buckets()
	cache: dict[str, str | None] = {}
	fallback = default_treatment if default_treatment in (VATABLE, EXEMPT, ZERO_RATED) else VATABLE
	vat_rate = _doc_vat_rate(doc)
	for item in (items if items is not None else getattr(doc, "items", None)) or []:
		item_amt = _print_line_amount(item, vat_rate)
		buckets[_item_treatment(item, fallback, cache)] += item_amt
	return buckets


def _item_treatment(item, default_treatment: str, cache: dict[str, str | None]) -> str:
	classified = _classify_text(str(_row_value(item, "vat_treatment") or ""))
	if classified:
		return classified

	from_rate = _treatment_from_item_tax_rate(item)
	if from_rate:
		return from_rate

	template_name = str(_row_value(item, "item_tax_template") or "").strip()
	if template_name:
		if template_name not in cache:
			cache[template_name] = _treatment_from_item_tax_template(template_name)
		if cache[template_name]:
			return cache[template_name]

	return default_treatment


def _treatment_from_item_tax_rate(item) -> str | None:
	found: list[str] = []
	for account in _parse_item_tax_rate(_row_value(item, "item_tax_rate")):
		account = str(account or "")
		treatment = _classify_text(account) or _classify_text(_account_name(account))
		if treatment:
			found.append(treatment)
	return _pick_treatment(found)


def _parse_item_tax_rate(raw) -> dict:
	if not raw:
		return {}
	if isinstance(raw, dict):
		return raw
	if isinstance(raw, str):
		try:
			parsed = json.loads(raw)
		except Exception:
			return {}
		return parsed if isinstance(parsed, dict) else {}
	return {}


def _pick_treatment(found: list[str]) -> str | None:
	if ZERO_RATED in found:
		return ZERO_RATED
	if EXEMPT in found:
		return EXEMPT
	if VATABLE in found:
		return VATABLE
	return None


def _treatment_from_item_tax_template(template_name: str) -> str | None:
	found: list[str] = []
	for rate in _item_tax_template_rates(template_name):
		if _row_value(rate, "not_applicable"):
			continue
		tax_type = str(_row_value(rate, "tax_type") or "")
		parts = [tax_type]
		if tax_type:
			account_name = _account_name(tax_type)
			if account_name:
				parts.append(account_name)
		treatment = _classify_text(" ".join(parts))
		if treatment:
			found.append(treatment)
	return _pick_treatment(found) or _classify_text(template_name)


def _item_tax_template_rates(template_name: str) -> list:
	for parent in _item_tax_template_parents(template_name):
		try:
			rows = (
				frappe.db.get_all(
					"Item Tax Template Detail",
					filters={"parent": parent},
					fields=["tax_type", "tax_rate", "not_applicable"],
				)
				or []
			)
		except Exception:
			rows = []
		if rows:
			return rows
	return []


def _item_tax_template_parents(template_name: str) -> list[str]:
	names = [template_name]
	try:
		by_title = (
			frappe.db.get_all(
				"Item Tax Template",
				filters={"title": template_name},
				pluck="name",
			)
			or []
		)
	except Exception:
		by_title = []
	for name in by_title:
		if name and name not in names:
			names.append(str(name))
	return names


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
	normalized = re.sub(r"[\s\-_]+", " ", label).strip()
	if "zero rated" in normalized:
		return ZERO_RATED
	if "exempt" in normalized:
		return EXEMPT
	if "vatable" in normalized or "vat" in normalized:
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
