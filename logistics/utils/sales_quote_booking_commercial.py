# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Commercial header fields (Incoterm, Broker) when creating bookings from a Sales Quote."""

from __future__ import annotations

from typing import Any

import frappe

_SALES_QUOTE_SCOPE_HEADER_COMMERCIAL_FIELDS: tuple[str, ...] = (
	"incoterm",
	"incoterm_place",
)


def _norm(value: Any) -> str:
	if value is None:
		return ""
	return str(value).strip()


def resolve_sales_quote_customs_broker(
	sq_doc: Any, scope_row: Any | None = None
) -> str | None:
	"""Customs broker from scope row, quote header, or first linked Customs service."""
	if scope_row is not None:
		cb = _norm(getattr(scope_row, "customs_broker", None))
		if cb:
			return cb
		if isinstance(scope_row, dict):
			cb = _norm(scope_row.get("customs_broker"))
			if cb:
				return cb

	cb = _norm(getattr(sq_doc, "customs_broker", None))
	if cb:
		return cb

	sq_name = _norm(getattr(sq_doc, "name", None))
	if not sq_name:
		return None

	from logistics.logistics.doctype.linked_service.linked_service import (
		get_linked_services_for_sales_quote,
	)

	for ls in get_linked_services_for_sales_quote(sq_name):
		cb = _norm(getattr(ls, "customs_broker", None))
		if cb:
			return cb
	return None


def apply_sales_quote_commercial_fields_to_operational_doc(
	target_doc: Any,
	sq_doc: Any,
	*,
	scope_row: Any | None = None,
	overwrite_incoterm: bool = True,
) -> None:
	"""Apply Sales Quote Incoterm and Customs Broker onto a new booking/order.

	When the quote has Incoterm, it wins over party/settings defaults (same as Sea Booking).
	Customs Broker from linked services maps to ``broker`` (Air/Sea Booking) or
	``customs_broker`` (Declaration Order) when still empty.
	"""
	if not target_doc or not sq_doc:
		return
	meta = frappe.get_meta(target_doc.doctype)

	for fn in _SALES_QUOTE_SCOPE_HEADER_COMMERCIAL_FIELDS:
		if not meta.get_field(fn):
			continue
		val = getattr(sq_doc, fn, None)
		if not _norm(val):
			continue
		cur = getattr(target_doc, fn, None)
		if overwrite_incoterm or not _norm(cur):
			target_doc.set(fn, val)

	cb = resolve_sales_quote_customs_broker(sq_doc, scope_row)
	if not cb:
		return
	if meta.get_field("customs_broker") and not _norm(getattr(target_doc, "customs_broker", None)):
		target_doc.customs_broker = cb
	if meta.get_field("broker") and not _norm(getattr(target_doc, "broker", None)):
		target_doc.broker = cb
