# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class SalesQuotePercentageBreak(Document):
	pass


@frappe.whitelist()
def save_percentage_breaks_for_reference(reference_doctype, reference_no, percentage_breaks, record_type):
	"""Save percentage break records for any charge reference doctype."""
	try:
		if not reference_doctype or not reference_no:
			return {"success": False, "error": "Reference doctype and reference no are required"}

		if isinstance(percentage_breaks, str):
			percentage_breaks = json.loads(percentage_breaks) if percentage_breaks else []

		frappe.db.delete(
			"Sales Quote Percentage Break",
			{"reference_doctype": reference_doctype, "reference_no": reference_no, "type": record_type},
		)
		for pb in percentage_breaks or []:
			if not pb.get("value_break") and not pb.get("percentage_rate"):
				continue
			doc = frappe.new_doc("Sales Quote Percentage Break")
			doc.reference_doctype = reference_doctype
			doc.reference_no = reference_no
			doc.type = record_type
			doc.rate_type = pb.get("rate_type") or "N (Normal)"
			doc.value_break = flt(pb.get("value_break", 0))
			doc.percentage_rate = flt(pb.get("percentage_rate", 0))
			doc.currency = pb.get("currency") or "USD"
			doc.insert(ignore_permissions=True)
		frappe.db.commit()
		return {"success": True}
	except Exception as e:
		frappe.log_error(f"Error saving percentage breaks: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_percentage_breaks(reference_doctype, reference_no, record_type="Selling"):
	"""Get list of percentage break records for a reference (for dialog editing)."""
	try:
		if not reference_doctype or not reference_no:
			return {"success": False, "percentage_breaks": []}
		percentage_breaks = frappe.get_all(
			"Sales Quote Percentage Break",
			filters={
				"reference_doctype": reference_doctype,
				"reference_no": reference_no,
				"type": record_type,
			},
			fields=["value_break", "percentage_rate", "rate_type", "currency"],
			order_by="value_break asc",
		)
		return {"success": True, "percentage_breaks": percentage_breaks or []}
	except Exception as e:
		frappe.log_error(f"Error getting percentage breaks: {str(e)}")
		return {"success": False, "percentage_breaks": []}
