# Copyright (c) 2026, www.agilasoft.com
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint


class PricingCenterSettings(Document):
	"""Per-company settings for Pricing Center."""
	pass


@frappe.whitelist()
def get_valid_until_offset(company: str | None = None) -> int:
	"""Return Valid Until offset in days for the given company (fallback to 30)."""
	if not company:
		return 30
	try:
		value = frappe.db.get_value("Pricing Center Settings", {"company": company}, "valid_until_offset_days")
		return cint(value) if value is not None else 30
	except Exception:
		return 30


def get_crm_sales_quote_settings(company: str | None = None) -> frappe._dict:
	"""Per-company CRM Sales Quote flags (Lead/Prospect creation)."""
	defaults = frappe._dict(
		allow_sales_quote_from_lead=0,
		allow_sales_quote_from_prospect=0,
	)
	if not company:
		return defaults
	try:
		row = frappe.db.get_value(
			"Pricing Center Settings",
			{"company": company},
			["allow_sales_quote_from_lead", "allow_sales_quote_from_prospect"],
			as_dict=True,
		)
	except Exception:
		return defaults
	if not row:
		return defaults
	return frappe._dict(
		allow_sales_quote_from_lead=cint(row.allow_sales_quote_from_lead),
		allow_sales_quote_from_prospect=cint(row.allow_sales_quote_from_prospect),
	)


@frappe.whitelist()
def get_crm_sales_quote_settings_for_desk(company: str | None = None) -> dict:
	"""Desk helper for CRM Sales Quote settings."""
	return dict(get_crm_sales_quote_settings(company))

