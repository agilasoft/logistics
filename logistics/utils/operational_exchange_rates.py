# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Build ``operational_exchange_rates`` child tables on bookings/shipments from Sales Quote Charge rows."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional, Union

import frappe
from frappe import _
from frappe.utils import flt, getdate

Row = Union[Mapping[str, Any], Any]


def _get(row: Row, key: str, default=None):
	if row is None:
		return default
	if isinstance(row, Mapping):
		return row.get(key, default)
	return getattr(row, key, default)


@frappe.whitelist()
def get_exchange_rate_for_source_currency_date(
	exchange_rate_source: Optional[str] = None,
	currency: Optional[str] = None,
	as_of_date: Optional[str] = None,
) -> Optional[float]:
	"""Return the company-base rate for *currency* from *Source Exchange Rate* as of *as_of_date*.

	Uses an exact (source, currency, date) row if present; otherwise the latest row with
	``date`` on or before *as_of_date* for the same source and currency.
	"""
	if not (exchange_rate_source and currency and as_of_date):
		return None
	as_of = getdate(as_of_date)
	exact = frappe.db.get_value(
		"Source Exchange Rate",
		{
			"exchange_rate_source": exchange_rate_source,
			"currency": currency,
			"date": as_of,
		},
		"exchange_rate",
	)
	if exact is not None:
		return float(exact)
	row = frappe.db.sql(
		"""
		select exchange_rate from `tabSource Exchange Rate`
		where exchange_rate_source = %(src)s and currency = %(cur)s and date <= %(d)s
		order by date desc
		limit 1
		""",
		{"src": exchange_rate_source, "cur": currency, "d": as_of},
		as_dict=True,
	)
	if row:
		return float(row[0]["exchange_rate"])
	return None


def resolve_single_operational_exchange_rate_row(row: Row) -> None:
	"""When Source, Currency, and Date are set, set ``rate`` from Source Exchange Rate master."""
	src = _get(row, "exchange_rate_source")
	cur = _get(row, "currency")
	dt = _get(row, "exchange_rate_date")
	if src and cur and dt:
		fetched = get_exchange_rate_for_source_currency_date(src, cur, dt)
		if fetched is not None:
			if isinstance(row, Mapping):
				row["rate"] = fetched
			else:
				row.rate = fetched

	if flt(_get(row, "rate")) == 0:
		frappe.throw(
			_(
				"Operational Exchange Rate: set Rate manually, or set Source, Currency, and Date so the rate can be loaded from Source Exchange Rate."
			),
			title=_("Missing rate"),
		)


def resolve_operational_exchange_rate_rows(parent_doc) -> None:
	"""Resolve rates on each operational exchange rate row (used from parent ``before_save``)."""
	for row in parent_doc.get("operational_exchange_rates") or []:
		resolve_single_operational_exchange_rate_row(row)


def apply_operational_exchange_rates_to_charge_rows(parent_doc) -> None:
	"""Copy resolved operational rates (and date) onto matching charge lines for the same entity."""
	if not parent_doc.meta.get_field("charges"):
		return
	for ox in parent_doc.get("operational_exchange_rates") or []:
		entity_type = getattr(ox, "entity_type", None)
		entity = getattr(ox, "entity", None)
		cur = getattr(ox, "currency", None)
		src = getattr(ox, "exchange_rate_source", None) or ""
		r = getattr(ox, "rate", None)
		dt = getattr(ox, "exchange_rate_date", None)
		if not entity_type or not entity or not cur or r is None:
			continue
		for ch in parent_doc.get("charges") or []:
			if entity_type == "Customer":
				if getattr(ch, "bill_to", None) != entity:
					continue
				if getattr(ch, "currency", None) != cur:
					continue
				if (getattr(ch, "bill_to_exchange_rate_source", None) or "") != src:
					continue
				ch.bill_to_exchange_rate = r
				if frappe.get_meta(ch.doctype).has_field("bill_to_exchange_rate_date"):
					ch.bill_to_exchange_rate_date = dt
			elif entity_type == "Supplier":
				if getattr(ch, "pay_to", None) != entity:
					continue
				cost_cur = getattr(ch, "cost_currency", None)
				if cost_cur != cur:
					continue
				if (getattr(ch, "pay_to_exchange_rate_source", None) or "") != src:
					continue
				ch.pay_to_exchange_rate = r
				if frappe.get_meta(ch.doctype).has_field("pay_to_exchange_rate_date"):
					ch.pay_to_exchange_rate_date = dt


def on_before_save_operational_exchange_rates(doc, method=None) -> None:
	if not doc.meta.get_field("operational_exchange_rates"):
		return
	resolve_operational_exchange_rate_rows(doc)
	if doc.meta.get_field("charges"):
		apply_operational_exchange_rates_to_charge_rows(doc)


def sync_operational_exchange_rates_from_charge_rows(parent_doc, charge_rows: Iterable[Row]) -> None:
	"""Populate ``operational_exchange_rates`` from operational charge lines.

	Deduplicates by (entity_type, entity, exchange_rate_source, currency, exchange_rate_date). First non-duplicate wins.
	"""
	parent_doc.set("operational_exchange_rates", [])
	seen = set()

	def add_row(
		entity_type: str,
		entity: Optional[str],
		source: Optional[str],
		currency: Optional[str],
		rate: Any,
		exchange_rate_date: Optional[str] = None,
	):
		if not entity or not currency:
			return
		try:
			rf = float(rate) if rate is not None and rate != "" else None
		except (TypeError, ValueError):
			rf = None
		if rf is None and not (source and exchange_rate_date):
			return
		key = (entity_type, entity, source or "", currency, str(exchange_rate_date or ""))
		if key in seen:
			return
		seen.add(key)
		row = parent_doc.append("operational_exchange_rates", {})
		row.entity_type = entity_type
		row.entity = entity
		row.exchange_rate_source = source
		row.currency = currency
		if exchange_rate_date:
			row.exchange_rate_date = exchange_rate_date
		if rf is not None:
			row.rate = rf

	for cr in charge_rows or []:
		bill_to = _get(cr, "bill_to")
		bxr = _get(cr, "bill_to_exchange_rate")
		b_src = _get(cr, "bill_to_exchange_rate_source")
		b_date = _get(cr, "bill_to_exchange_rate_date")
		cur = _get(cr, "currency")
		if bill_to and cur:
			add_row("Customer", bill_to, b_src, cur, bxr, b_date)

		pay_to = _get(cr, "pay_to")
		pxr = _get(cr, "pay_to_exchange_rate")
		p_src = _get(cr, "pay_to_exchange_rate_source")
		p_date = _get(cr, "pay_to_exchange_rate_date")
		cc = _get(cr, "cost_currency")
		if pay_to and cc:
			add_row("Supplier", pay_to, p_src, cc, pxr, p_date)
