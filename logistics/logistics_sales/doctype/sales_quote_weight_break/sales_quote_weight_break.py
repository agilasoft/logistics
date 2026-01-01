# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SalesQuoteWeightBreak(Document):
	def validate(self):
		"""Validate the weight break record"""
		# Ensure reference fields are set
		if not self.reference_doctype:
			frappe.throw("Reference Doctype is required")
		
		if not self.reference_no:
			frappe.throw("Reference No is required")
		
		if not self.type:
			frappe.throw("Type is required (Selling or Cost)")


@frappe.whitelist()
def save_weight_breaks_for_air_freight(air_freight_name, weight_breaks, record_type="Selling"):
	"""
	Save weight break records for a Sales Quote Air Freight record
	
	Args:
		air_freight_name: Name of the Sales Quote Air Freight record
		weight_breaks: List of weight break data
		record_type: "Selling" or "Cost"
		
	Returns:
		Success status
	"""
	try:
		if isinstance(weight_breaks, str):
			import json
			weight_breaks = json.loads(weight_breaks)
		
		# Delete existing weight breaks for this air freight and type
		existing = frappe.get_all(
			"Sales Quote Weight Break",
			filters={
				"reference_doctype": "Sales Quote Air Freight",
				"reference_no": air_freight_name,
				"type": record_type
			},
			pluck="name"
		)
		
		for name in existing:
			frappe.delete_doc("Sales Quote Weight Break", name, ignore_permissions=True)
		
		# Create new weight break records
		for wb in weight_breaks:
			doc = frappe.new_doc("Sales Quote Weight Break")
			doc.reference_doctype = "Sales Quote Air Freight"
			doc.reference_no = air_freight_name
			doc.type = record_type
			doc.rate_type = wb.get("rate_type")
			doc.weight_break = wb.get("weight_break")
			doc.unit_rate = wb.get("unit_rate")
			doc.insert(ignore_permissions=True)
		
		frappe.db.commit()
		
		return {
			"success": True,
			"message": f"Saved {len(weight_breaks)} weight break records"
		}
		
	except Exception as e:
		frappe.log_error(f"Error saving weight breaks: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}
