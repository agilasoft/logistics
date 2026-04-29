# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Company base currency and operational exchange rate line conversion (incl. triangulation)."""

from __future__ import annotations

from typing import Any, Optional, Sequence

import frappe
from frappe.model.document import Document


def get_company_base_currency(company: Optional[str]) -> Optional[str]:
	if not company:
		return frappe.defaults.get_global_default("currency")
	return frappe.db.get_value("Company", company, "default_currency")


def _iter_rows(
	rows: Sequence[Any],
	*,
	entity_type: Optional[str] = None,
	entity: Optional[str] = None,
):
	for row in rows or []:
		if entity_type and getattr(row, "entity_type", None) and row.entity_type != entity_type:
			continue
		if entity and getattr(row, "entity", None) and row.entity != entity:
			continue
		yield row


def _rate_to_base_for_currency(
	rows: Sequence[Any],
	currency: str,
	base: str,
	*,
	entity_type: Optional[str] = None,
	entity: Optional[str] = None,
) -> Optional[float]:
	"""Return company-base units per 1 unit of *currency* (same as row.rate), or 1.0 if currency is base."""
	if currency == base:
		return 1.0
	for row in _iter_rows(rows, entity_type=entity_type, entity=entity):
		if getattr(row, "currency", None) != currency:
			continue
		r = getattr(row, "rate", None)
		if r is not None:
			return float(r)
	return None


def convert_amount_via_operational_rows(
	amount: float,
	from_currency: str,
	to_currency: str,
	doc: Document,
	*,
	entity_type: Optional[str] = None,
	entity: Optional[str] = None,
) -> Optional[float]:
	"""Convert *amount* using ``operational_exchange_rates`` on *doc*.

	- Row ``rate`` = company base per 1 unit of ``currency``.
	- Optional same-row third currency: ``alternate_rate`` = units of ``alternate_currency`` per 1 ``currency``.
	- Otherwise triangulate via company base using two (or one) rate rows.
	"""
	if from_currency == to_currency:
		return float(amount)

	rows = list(doc.get("operational_exchange_rates") or [])

	# Direct third-currency leg on a single row
	for row in _iter_rows(rows, entity_type=entity_type, entity=entity):
		cur = getattr(row, "currency", None)
		alt = getattr(row, "alternate_currency", None)
		ar = getattr(row, "alternate_rate", None)
		if not cur or not alt or ar is None:
			continue
		if cur == from_currency and alt == to_currency:
			return float(amount) * float(ar)
		if cur == to_currency and alt == from_currency and float(ar) != 0:
			return float(amount) / float(ar)

	base = get_company_base_currency(getattr(doc, "company", None))
	if not base:
		return None

	r_from = _rate_to_base_for_currency(
		rows, from_currency, base, entity_type=entity_type, entity=entity
	)
	r_to = _rate_to_base_for_currency(
		rows, to_currency, base, entity_type=entity_type, entity=entity
	)
	if r_from is None or r_to is None:
		return None
	if r_to == 0:
		return None
	# amount in base = amount_from * r_from; amount_to = amount_in_base / r_to
	return float(amount) * float(r_from) / float(r_to)
