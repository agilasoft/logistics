# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Build ``operational_exchange_rates`` child tables on bookings/shipments from Sales Quote Charge rows."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional, Union

Row = Union[Mapping[str, Any], Any]


def _get(row: Row, key: str, default=None):
	if row is None:
		return default
	if isinstance(row, Mapping):
		return row.get(key, default)
	return getattr(row, key, default)


def sync_operational_exchange_rates_from_charge_rows(parent_doc, charge_rows: Iterable[Row]) -> None:
	"""Populate ``operational_exchange_rates`` from operational charge lines.

	Deduplicates by (entity_type, entity, exchange_rate_source, currency). First non-duplicate wins.
	"""
	parent_doc.set("operational_exchange_rates", [])
	seen = set()

	def add_row(
		entity_type: str,
		entity: Optional[str],
		source: Optional[str],
		currency: Optional[str],
		rate: Any,
	):
		if not entity or not currency:
			return
		if rate is None:
			return
		try:
			rf = float(rate)
		except (TypeError, ValueError):
			return
		key = (entity_type, entity, source or "", currency)
		if key in seen:
			return
		seen.add(key)
		row = parent_doc.append("operational_exchange_rates", {})
		row.entity_type = entity_type
		row.entity = entity
		row.exchange_rate_source = source
		row.currency = currency
		row.rate = rf

	for cr in charge_rows or []:
		bill_to = _get(cr, "bill_to")
		bxr = _get(cr, "bill_to_exchange_rate")
		b_src = _get(cr, "bill_to_exchange_rate_source")
		cur = _get(cr, "currency")
		if bill_to and cur:
			add_row("Customer", bill_to, b_src, cur, bxr)

		pay_to = _get(cr, "pay_to")
		pxr = _get(cr, "pay_to_exchange_rate")
		p_src = _get(cr, "pay_to_exchange_rate_source")
		cc = _get(cr, "cost_currency")
		if pay_to and cc:
			add_row("Supplier", pay_to, p_src, cc, pxr)
