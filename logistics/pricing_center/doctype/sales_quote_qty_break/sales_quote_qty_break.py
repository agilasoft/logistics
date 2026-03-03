# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class SalesQuoteQtyBreak(Document):
	pass


@frappe.whitelist()
def save_qty_breaks_for_reference(reference_doctype, reference_no, qty_breaks, record_type):
	"""Save qty break records for any doctype (Sales Quote Air Freight, Air Booking Charges, etc.)."""
	try:
		if not reference_doctype or not reference_no:
			return {"success": False, "error": "Reference doctype and reference no are required"}

		if isinstance(qty_breaks, str):
			qty_breaks = json.loads(qty_breaks) if qty_breaks else []

		frappe.db.delete(
			"Sales Quote Qty Break",
			{"reference_doctype": reference_doctype, "reference_no": reference_no, "type": record_type},
		)
		for qb in qty_breaks or []:
			if not qb.get("qty_break") and not qb.get("unit_rate"):
				continue
			doc = frappe.new_doc("Sales Quote Qty Break")
			doc.reference_doctype = reference_doctype
			doc.reference_no = reference_no
			doc.type = record_type
			doc.rate_type = qb.get("rate_type") or "Qty Break"
			doc.qty_break = flt(qb.get("qty_break", 0))
			doc.unit_rate = flt(qb.get("unit_rate", 0))
			doc.currency = qb.get("currency") or "USD"
			doc.insert(ignore_permissions=True)
		frappe.db.commit()
		return {"success": True}
	except Exception as e:
		frappe.log_error(f"Error saving qty breaks: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_qty_breaks(reference_doctype, reference_no, record_type="Selling"):
	"""Get list of qty break records for a reference (for dialog editing)."""
	try:
		if not reference_doctype or not reference_no:
			return {"success": False, "qty_breaks": []}
		qty_breaks = frappe.get_all(
			"Sales Quote Qty Break",
			filters={
				"reference_doctype": reference_doctype,
				"reference_no": reference_no,
				"type": record_type,
			},
			fields=["qty_break", "unit_rate", "rate_type", "currency"],
			order_by="qty_break asc",
		)
		return {"success": True, "qty_breaks": qty_breaks or []}
	except Exception as e:
		frappe.log_error(f"Error getting qty breaks: {str(e)}")
		return {"success": False, "qty_breaks": []}
