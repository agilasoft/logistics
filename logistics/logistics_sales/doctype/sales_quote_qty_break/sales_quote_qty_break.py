# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SalesQuoteQtyBreak(Document):
	def validate(self):
		"""Validate the qty break record"""
		# Ensure reference fields are set
		if not self.reference_doctype:
			frappe.throw("Reference Doctype is required")
		
		if not self.reference_no:
			frappe.throw("Reference No is required")
		
		if not self.type:
			frappe.throw("Type is required (Selling or Cost)")


@frappe.whitelist()
def save_qty_breaks_for_air_freight(air_freight_name, qty_breaks, record_type="Selling"):
	"""
	Save qty break records for a Sales Quote Air Freight record
	
	Args:
		air_freight_name: Name of the Sales Quote Air Freight record
		qty_breaks: List of qty break data
		record_type: "Selling" or "Cost"
		
	Returns:
		Success status
	"""
	try:
		if isinstance(qty_breaks, str):
			import json
			qty_breaks = json.loads(qty_breaks)
		
		# Delete existing qty breaks for this air freight and type
		existing = frappe.get_all(
			"Sales Quote Qty Break",
			filters={
				"reference_doctype": "Sales Quote Air Freight",
				"reference_no": air_freight_name,
				"type": record_type
			},
			pluck="name"
		)
		
		for name in existing:
			frappe.delete_doc("Sales Quote Qty Break", name, ignore_permissions=True)
		
		# Create new qty break records
		for qb in qty_breaks:
			doc = frappe.new_doc("Sales Quote Qty Break")
			doc.reference_doctype = "Sales Quote Air Freight"
			doc.reference_no = air_freight_name
			doc.type = record_type
			doc.rate_type = qb.get("rate_type")
			doc.qty_break = qb.get("qty_break")
			doc.unit_rate = qb.get("unit_rate")
			doc.currency = qb.get("currency")
			doc.insert(ignore_permissions=True)
		
		frappe.db.commit()
		
		return {
			"success": True,
			"message": f"Saved {len(qty_breaks)} qty break records"
		}
		
	except Exception as e:
		frappe.log_error(f"Error saving qty breaks: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}
