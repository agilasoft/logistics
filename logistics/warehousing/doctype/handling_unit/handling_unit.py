# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class HandlingUnit(Document):
	pass


@frappe.whitelist()
def is_location_overflow_enabled(company):
	"""Check if location overflow is enabled for a company"""
	if not company:
		return False
	try:
		settings = frappe.get_doc("Warehouse Settings", company)
		return bool(getattr(settings, "enable_location_overflow", False))
	except (frappe.DoesNotExistError, AttributeError):
		return False
