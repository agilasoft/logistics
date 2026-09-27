# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document


class SalesQuoteSpecifiedCharge(Document):
	pass


@frappe.whitelist()
def save_specified_charges_for_reference(
	reference_doctype, reference_no, specified_charges, record_type
):
	"""Save specified charge item rows for any charge reference doctype."""
	try:
		if not reference_doctype or not reference_no:
			return {"success": False, "error": "Reference doctype and reference no are required"}

		if isinstance(specified_charges, str):
			specified_charges = json.loads(specified_charges) if specified_charges else []

		frappe.db.delete(
			"Sales Quote Specified Charge",
			{
				"reference_doctype": reference_doctype,
				"reference_no": reference_no,
				"type": record_type,
				"selection_kind": "Item",
			},
		)
		for row in specified_charges or []:
			item_code = (row.get("item_code") or "").strip()
			if not item_code:
				continue
			doc = frappe.new_doc("Sales Quote Specified Charge")
			doc.reference_doctype = reference_doctype
			doc.reference_no = reference_no
			doc.type = record_type
			doc.selection_kind = "Item"
			doc.item_code = item_code
			doc.insert(ignore_permissions=True)
		frappe.db.commit()
		return {"success": True}
	except Exception as e:
		frappe.log_error(f"Error saving specified charges: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_specified_charges(reference_doctype, reference_no, record_type="Selling"):
	"""Get specified charge items for a reference (for dialog editing)."""
	try:
		if not reference_doctype or not reference_no:
			return {"success": False, "specified_charges": []}
		specified_charges = frappe.get_all(
			"Sales Quote Specified Charge",
			filters={
				"reference_doctype": reference_doctype,
				"reference_no": reference_no,
				"type": record_type,
				"selection_kind": "Item",
			},
			fields=["item_code"],
			order_by="creation asc",
		)
		return {"success": True, "specified_charges": specified_charges or []}
	except Exception as e:
		frappe.log_error(f"Error getting specified charges: {str(e)}")
		return {"success": False, "specified_charges": []}


@frappe.whitelist()
def get_charge_row_specified_multiselect(reference_doctype, reference_no):
	"""Load persisted multiselect values for a charge row (items + charge groups)."""
	from logistics.utils.specified_charges_persistence import (
		load_specified_charge_groups,
		load_specified_items,
	)

	if not reference_doctype or not reference_no:
		return {"success": False}

	return {
		"success": True,
		"selling_specified_items": load_specified_items(reference_doctype, reference_no, "Selling"),
		"cost_specified_items": load_specified_items(reference_doctype, reference_no, "Cost"),
		"selling_specified_charge_groups": load_specified_charge_groups(
			reference_doctype, reference_no, "Selling"
		),
		"cost_specified_charge_groups": load_specified_charge_groups(
			reference_doctype, reference_no, "Cost"
		),
	}
