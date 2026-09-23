# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document
from frappe.utils import flt


UNIT_BREAK_LIST_FIELDS = (
	"unit_type",
	"container_type",
	"unit_break",
	"unit_rate",
	"currency",
)


class ChargeUnitBreak(Document):
	def before_insert(self):
		# Dynamic Link to charge child names; skip strict link checks (unsaved/hash names).
		self.flags.ignore_links = True

	def before_save(self):
		self.flags.ignore_links = True


def is_container_unit_type(unit_type) -> bool:
	return (unit_type or "").strip().lower() == "container"


def _row_is_empty(row) -> bool:
	if (row.get("container_type") or "").strip():
		return False
	if flt(row.get("unit_break")):
		return False
	if flt(row.get("unit_rate")):
		return False
	return True


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
			if not isinstance(row, dict) or _row_is_empty(row):
				continue
			doc = frappe.new_doc("Charge Unit Break")
			doc.reference_doctype = reference_doctype
			doc.reference_no = reference_no
			doc.type = record_type
			doc.unit_type = unit_type or row.get("unit_type") or ""
			doc.container_type = (row.get("container_type") or "").strip() or None
			doc.unit_break = flt(row.get("unit_break", 0))
			doc.unit_rate = flt(row.get("unit_rate", 0))
			doc.currency = row.get("currency") or "USD"
			doc.insert(ignore_permissions=True, ignore_links=True)
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
		meta = frappe.get_meta("Charge Unit Break")
		fields = [f for f in UNIT_BREAK_LIST_FIELDS if meta.has_field(f)]
		unit_breaks = frappe.get_all(
			"Charge Unit Break",
			filters={
				"reference_doctype": reference_doctype,
				"reference_no": reference_no,
				"type": record_type,
			},
			fields=fields,
			order_by="container_type asc, unit_break asc" if meta.has_field("container_type") else "unit_break asc",
		)
		return {"success": True, "unit_breaks": unit_breaks or []}
	except Exception as e:
		frappe.log_error(f"Error getting unit breaks: {str(e)}")
		return {"success": False, "unit_breaks": []}
