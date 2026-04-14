# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Sales Quote valid_until: block creation when expired; warn when operating dates exceed validity."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import format_date, getdate, today

from logistics.utils.module_integration import _resolve_sales_quote_from_doc

# (fieldname, label_key) — label_key is field label for messages
DOCTYPE_OPERATING_DATE_FIELDS: dict[str, tuple[tuple[str, str], ...]] = {
	"Air Booking": (("booking_date", "Booking Date"), ("etd", "ETD")),
	"Sea Booking": (("booking_date", "Booking Date"), ("etd", "ETD")),
	"Air Shipment": (("booking_date", "Booking Date"), ("etd", "ETD")),
	"Sea Shipment": (("booking_date", "Booking Date"), ("etd", "ETD")),
	"Transport Order": (("booking_date", "Booking Date"), ("scheduled_date", "Scheduled Date")),
	"Transport Job": (("booking_date", "Booking Date"), ("scheduled_date", "Scheduled Date")),
	"Declaration Order": (("order_date", "Order Date"), ("etd", "ETD"), ("eta", "ETA")),
}


def throw_if_sales_quote_expired_for_creation(sales_quote) -> None:
	"""Block creating bookings/orders/shipments from a Sales Quote after its Valid Until date."""
	if isinstance(sales_quote, str):
		if not sales_quote or not frappe.db.exists("Sales Quote", sales_quote):
			return
		vu = frappe.db.get_value("Sales Quote", sales_quote, "valid_until")
	else:
		vu = getattr(sales_quote, "valid_until", None)
	if not vu:
		return
	if getdate(today()) > getdate(vu):
		frappe.throw(
			_(
				"This Sales Quote is no longer valid (Valid Until: {0}). Renew or extend the quotation before creating a booking or order."
			).format(format_date(vu)),
			title=_("Sales Quote Expired"),
		)


def _linked_sales_quote_name(doc) -> str | None:
	return _resolve_sales_quote_from_doc(doc)


def _valid_until_for_doc(doc) -> tuple[str | None, object | None]:
	sq = _linked_sales_quote_name(doc)
	if not sq:
		return None, None
	vu = frappe.db.get_value("Sales Quote", sq, "valid_until")
	return sq, vu


def collect_sales_quote_validity_warnings(doc):
	"""Return (sales_quote_name, valid_until, expired_as_of_today, list of (field_label, field_value))."""
	sq, vu = _valid_until_for_doc(doc)
	if not sq or not vu:
		return sq, vu, False, []
	vu_d = getdate(vu)
	expired = getdate(today()) > vu_d
	fields = DOCTYPE_OPERATING_DATE_FIELDS.get(doc.doctype)
	if not fields:
		return sq, vu, expired, []
	past = []
	for fn, label in fields:
		val = getattr(doc, fn, None)
		if val and getdate(val) > vu_d:
			past.append((label, val))
	return sq, vu, expired, past


def msgprint_sales_quote_validity_warnings(doc) -> None:
	"""Non-blocking warnings on save when a linked Sales Quote is expired or operating dates exceed Valid Until."""
	if getattr(doc.flags, "skip_sales_quote_validity_warning", False):
		return
	sq, vu, expired, past_dates = collect_sales_quote_validity_warnings(doc)
	if not sq or not vu:
		return
	lines = []
	vu_fmt = format_date(vu)
	if expired:
		lines.append(_("Sales Quote {0} has expired (Valid Until {1}).").format(sq, vu_fmt))
	for label, val in past_dates:
		lines.append(
			_("{0} ({1}) is after Sales Quote Valid Until ({2}).").format(
				_(label), format_date(val), vu_fmt
			)
		)
	if lines:
		frappe.msgprint(
			"<br>".join(lines),
			title=_("Sales Quote validity"),
			indicator="orange",
		)


def get_sales_quote_validity_dashboard_html(doc) -> str:
	"""Banner HTML for the Dashboard tab (prepend to existing dashboard HTML)."""
	if getattr(doc.flags, "skip_sales_quote_validity_dashboard", False):
		return ""
	sq, vu, expired, past_dates = collect_sales_quote_validity_warnings(doc)
	if not sq or not vu:
		return ""
	if not expired and not past_dates:
		return ""
	from frappe.utils import escape_html

	vu_fmt = escape_html(str(vu))
	sq_e = escape_html(sq)
	parts = []
	if expired:
		parts.append(
			'<div class="alert alert-warning" role="alert"><strong>'
			+ escape_html(_("Sales Quote expired"))
			+ "</strong>: "
			+ escape_html(_("Quotation"))
			+ f" {sq_e} — "
			+ escape_html(_("Valid Until"))
			+ f" {vu_fmt}.</div>"
		)
	for label, val in past_dates:
		parts.append(
			f'<div class="alert alert-warning" role="alert">'
			f"<strong>{escape_html(_(label))}</strong> ({escape_html(str(val))}) "
			f"{escape_html(_('is after Sales Quote Valid Until'))} ({vu_fmt}).</div>"
		)
	return "\n".join(parts)
