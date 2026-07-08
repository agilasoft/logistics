# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class ChargeUnitBreak(Document):
	pass


@frappe.whitelist()
def save_unit_breaks_for_reference(
	reference_doctype,
	reference_no,
	unit_breaks,
	record_type,
	unit_type=None,
):
	"""Save unit break tiers for any charge reference row."""
	try:
		if not reference_doctype or not reference_no:
			return {"success": False, "error": "Reference doctype and reference no are required"}

		if isinstance(unit_breaks, str):
			unit_breaks = json.loads(unit_breaks) if unit_breaks else []

		unit_type = (unit_type or "").strip()
		frappe.db.delete(
			"Charge Unit Break",
			{
				"reference_doctype": reference_doctype,
				"reference_no": reference_no,
				"type": record_type,
			},
		)
		for row in unit_breaks or []:
			if not flt(row.get("unit_break")) and not flt(row.get("unit_rate")):
				continue
			doc = frappe.new_doc("Charge Unit Break")
			doc.reference_doctype = reference_doctype
			doc.reference_no = reference_no
			doc.type = record_type
			doc.unit_type = unit_type or row.get("unit_type") or ""
			doc.unit_break = flt(row.get("unit_break", 0))
			doc.unit_rate = flt(row.get("unit_rate", 0))
			doc.currency = row.get("currency") or "USD"
			doc.insert(ignore_permissions=True)
		frappe.db.commit()
		return {"success": True}
	except Exception as e:
		frappe.log_error(f"Error saving unit breaks: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_unit_breaks(reference_doctype, reference_no, record_type="Selling"):
	"""Get unit break tiers for a charge reference row."""
	try:
		if not reference_doctype or not reference_no:
			return {"success": False, "unit_breaks": []}
		unit_breaks = frappe.get_all(
			"Charge Unit Break",
			filters={
				"reference_doctype": reference_doctype,
				"reference_no": reference_no,
				"type": record_type,
			},
			fields=["unit_type", "unit_break", "unit_rate", "currency"],
			order_by="unit_break asc",
		)
		return {"success": True, "unit_breaks": unit_breaks or []}
	except Exception as e:
		frappe.log_error(f"Error getting unit breaks: {str(e)}")
		return {"success": False, "unit_breaks": []}
