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

