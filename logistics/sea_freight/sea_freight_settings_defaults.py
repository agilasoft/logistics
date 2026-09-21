# Copyright (c) 2026, logistics.agilasoft.com and contributors
# For license information, please see license.txt
"""Apply Sea Freight Settings defaults (branch, cost center, profit center, incoterm, release type)."""

import frappe

from logistics.sea_freight.doctype.sea_freight_settings.sea_freight_settings import SeaFreightSettings


def _set_link_if_empty(doc, fieldname, doctype, value):
	if getattr(doc, fieldname, None) or not value:
		return
	if frappe.db.exists(doctype, value):
		setattr(doc, fieldname, value)


def _get_sea_freight_settings_for_doc(doc):
	company = getattr(doc, "company", None)
	if not company:
		return None
	try:
		return SeaFreightSettings.get_settings(company)
	except Exception:
		return None


def apply_accounting_defaults_from_sea_freight_settings(doc):
	"""Fill branch, cost center, and profit center from Sea Freight Settings when still empty.

	Does not overwrite user or quote-sourced values. Uses settings for the document company.
	"""
	if getattr(doc, "_sea_freight_settings_accounting_applied", None):
		return
	settings = _get_sea_freight_settings_for_doc(doc)
	if not settings:
		return

	_set_link_if_empty(doc, "branch", "Branch", getattr(settings, "default_branch", None))
	_set_link_if_empty(doc, "cost_center", "Cost Center", getattr(settings, "default_cost_center", None))
	_set_link_if_empty(doc, "profit_center", "Profit Center", getattr(settings, "default_profit_center", None))
	doc._sea_freight_settings_accounting_applied = True


def apply_incoterm_default_from_sea_freight_settings(doc):
	"""Fill empty Incoterm from Sea Freight Settings (last-priority fallback).

	Does not overwrite quote, consignee, shipper, or user values.
	"""
	if getattr(doc, "incoterm", None):
		return
	if not doc.meta.get_field("incoterm"):
		return
	settings = _get_sea_freight_settings_for_doc(doc)
	if not settings:
		return
	_set_link_if_empty(doc, "incoterm", "Incoterm", getattr(settings, "default_incoterm", None))


def valid_release_type(value):
	"""Return ``value`` when it is a real Release Type master, otherwise None."""
	if not value:
		return None
	if frappe.db.exists("Release Type", value):
		return value
	return None


def apply_release_type_default_from_sea_freight_settings(doc):
	"""Fill empty Release Type from Sea Freight Settings.

	Does not overwrite a value already set on the document.
	"""
	if getattr(doc, "release_type", None):
		return
	if not doc.meta.get_field("release_type"):
		return
	settings = _get_sea_freight_settings_for_doc(doc)
	if not settings:
		return
	_set_link_if_empty(
		doc, "release_type", "Release Type", getattr(settings, "default_release_type", None)
	)


def apply_release_type_from_sea_booking(shipment):
	"""Copy Sea Booking.release_type onto an empty Sea Shipment, then settings default."""
	if getattr(shipment, "release_type", None):
		return
	booking_name = (getattr(shipment, "sea_booking", None) or "").strip()
	if booking_name:
		booking_rt = valid_release_type(
			frappe.db.get_value("Sea Booking", booking_name, "release_type")
		)
		if booking_rt:
			shipment.release_type = booking_rt
			return
	apply_release_type_default_from_sea_freight_settings(shipment)


def _resolve_sales_quote_incoterm(doc, sales_quote=None):
	"""Return Sales Quote.incoterm when set (from doc or linked sales_quote)."""
	if sales_quote is not None:
		return getattr(sales_quote, "incoterm", None) or None
	sq_name = (getattr(doc, "sales_quote", None) or "").strip()
	if not sq_name:
		return None
	if not frappe.db.exists("Sales Quote", sq_name):
		return None
	return frappe.db.get_value("Sales Quote", sq_name, "incoterm")


def apply_sea_booking_incoterm_defaults(doc, sales_quote=None):
	"""Apply Sea Booking Incoterm priority: Quote (overwrite) → Consignee → Shipper → Settings.

	When the linked Sales Quote has an Incoterm, it always wins. Party and Settings
	defaults only fill when the field is still empty.
	"""
	if doc.meta.get_field("incoterm"):
		sq_incoterm = _resolve_sales_quote_incoterm(doc, sales_quote=sales_quote)
		if sq_incoterm:
			doc.incoterm = sq_incoterm

		from logistics.utils.shipper_consignee_defaults import apply_shipper_consignee_defaults

		apply_shipper_consignee_defaults(doc)
		apply_incoterm_default_from_sea_freight_settings(doc)

	apply_release_type_default_from_sea_freight_settings(doc)
