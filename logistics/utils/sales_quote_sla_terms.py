# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Copy Service Level (SLA) and Terms from Sales Quote onto bookings/orders.

Sales Quote stores SLA on ``service_code`` (Link → Logistics Service Level) and Terms on
``tc_name`` / ``terms``. Operational docs use different field names:

- Air / Sea Booking: ``service_level``, ``tc_name``, ``terms`` (Text Editor details)
- Transport Order: ``service_level``, ``terms`` (Link), ``terms_and_conditions_details``
- Declaration Order: ``service_level`` (no Terms fields)
"""

from __future__ import annotations

from typing import Any

import frappe


def _nonempty(value: Any) -> bool:
	return value is not None and str(value).strip() != ""


def _set_if_allowed(doc: Any, fieldname: str, value: Any, *, overwrite: bool) -> bool:
	if not frappe.get_meta(doc.doctype).has_field(fieldname):
		return False
	if not _nonempty(value):
		return False
	if not overwrite and _nonempty(getattr(doc, fieldname, None)):
		return False
	doc.set(fieldname, value)
	return True


def resolve_sales_quote_service_level(sales_quote: Any) -> str | None:
	"""Return the Logistics Service Level name from a Sales Quote (or dict-like)."""
	if not sales_quote:
		return None
	# Current field on Sales Quote; legacy ``service_level`` kept as fallback.
	for fn in ("service_code", "service_level", "logistics_service_level"):
		val = (
			sales_quote.get(fn)
			if isinstance(sales_quote, dict)
			else getattr(sales_quote, fn, None)
		)
		if _nonempty(val):
			return str(val).strip()
	return None


def resolve_sales_quote_terms_link(sales_quote: Any) -> str | None:
	"""Return the Terms and Conditions link name from a Sales Quote."""
	if not sales_quote:
		return None
	val = (
		sales_quote.get("tc_name")
		if isinstance(sales_quote, dict)
		else getattr(sales_quote, "tc_name", None)
	)
	return str(val).strip() if _nonempty(val) else None


def resolve_sales_quote_terms_details(sales_quote: Any) -> str | None:
	"""Return Terms and Conditions HTML/text from a Sales Quote."""
	if not sales_quote:
		return None
	val = (
		sales_quote.get("terms")
		if isinstance(sales_quote, dict)
		else getattr(sales_quote, "terms", None)
	)
	return val if _nonempty(val) else None


def apply_sales_quote_sla_and_terms(
	target_doc: Any,
	sales_quote: Any,
	*,
	overwrite: bool = False,
) -> None:
	"""Map Sales Quote SLA + Terms onto ``target_doc`` when matching fields exist.

	Args:
		target_doc: Booking/order being created or updated.
		sales_quote: Sales Quote doc, name, or dict with the relevant fields.
		overwrite: When True, replace existing target values with quote values.
			When False (default), only fill empty target fields (fetch / create).
	"""
	if not target_doc or not sales_quote:
		return

	if isinstance(sales_quote, str):
		if not frappe.db.exists("Sales Quote", sales_quote):
			return
		sales_quote = frappe.get_cached_doc("Sales Quote", sales_quote)

	meta = frappe.get_meta(target_doc.doctype)

	sla = resolve_sales_quote_service_level(sales_quote)
	sla_details = (
		sales_quote.get("service_level_details")
		if isinstance(sales_quote, dict)
		else getattr(sales_quote, "service_level_details", None)
	)
	if meta.has_field("service_level"):
		_set_if_allowed(target_doc, "service_level", sla, overwrite=overwrite)
	elif meta.has_field("logistics_service_level"):
		_set_if_allowed(target_doc, "logistics_service_level", sla, overwrite=overwrite)
	if meta.has_field("service_level_details"):
		_set_if_allowed(target_doc, "service_level_details", sla_details, overwrite=overwrite)

	tc_name = resolve_sales_quote_terms_link(sales_quote)
	terms_details = resolve_sales_quote_terms_details(sales_quote)

	if meta.has_field("tc_name"):
		_set_if_allowed(target_doc, "tc_name", tc_name, overwrite=overwrite)
		terms_df = meta.get_field("terms")
		if terms_df and terms_df.fieldtype == "Text Editor":
			_set_if_allowed(target_doc, "terms", terms_details, overwrite=overwrite)
		return

	# Transport Order-style: Terms link is ``terms``, details in ``terms_and_conditions_details``.
	terms_df = meta.get_field("terms")
	if terms_df and terms_df.fieldtype == "Link" and (terms_df.options or "") == "Terms and Conditions":
		_set_if_allowed(target_doc, "terms", tc_name, overwrite=overwrite)
		if meta.has_field("terms_and_conditions_details"):
			_set_if_allowed(
				target_doc, "terms_and_conditions_details", terms_details, overwrite=overwrite
			)
		return

	if terms_df and terms_df.fieldtype == "Text Editor":
		_set_if_allowed(target_doc, "terms", terms_details, overwrite=overwrite)
