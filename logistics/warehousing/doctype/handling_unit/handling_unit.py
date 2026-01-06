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
		# Try getting the value directly from the database first
		value = frappe.db.get_value("Warehouse Settings", company, "enable_location_overflow")
		if value is None:
			# If not found in DB, try getting the doc
			settings = frappe.get_doc("Warehouse Settings", company)
			value = getattr(settings, "enable_location_overflow", False)
		
		# Handle both integer (0/1) and boolean values
		# Check fields in Frappe are stored as 0/1 in database
		return bool(value) if value is not None else False
	except frappe.DoesNotExistError:
		return False
	except Exception as e:
		frappe.logger().error(f"Error checking location overflow for company {company}: {str(e)}")
		return False
