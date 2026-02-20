# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""API for Get Additional Charges and related job actions."""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt


JOB_QUOTE_MAP = {
	"Transport Job": ("transport", "Sales Quote Transport", "Transport Job Charges"),
	"Warehouse Job": ("warehousing", "Sales Quote Warehouse", "Warehouse Job Charges"),
	"Air Shipment": ("air_freight", "Sales Quote Air Freight", "Air Shipment Charges"),
	"Sea Shipment": ("sea_freight", "Sales Quote Sea Freight", "Sea Freight Charges"),
}


@frappe.whitelist()
def get_additional_charges(job_doctype, job_name, sales_quote_name):
	"""
	Apply charges from an Additional Charge Sales Quote to a job.
	Adds rows to the job's charges table with sales_quote_link set.
	Returns dict with success, message, charges_added.
	"""
	if not job_doctype or not job_name or not sales_quote_name:
		frappe.throw(_("Job DocType, Job name and Sales Quote are required."))
	if not frappe.db.exists(job_doctype, job_name):
		frappe.throw(_("Job {0} does not exist.").format(job_name))
	if not frappe.db.exists("Sales Quote", sales_quote_name):
		frappe.throw(_("Sales Quote {0} does not exist.").format(sales_quote_name))

	sq = frappe.db.get_value(
		"Sales Quote",
		sales_quote_name,
		["additional_charge", "job_type", "job"],
		as_dict=True,
	)
	if not sq or not sq.get("additional_charge"):
		frappe.throw(_("Sales Quote must be marked as Additional Charge and linked to a job."))
	if sq.get("job_type") != job_doctype or sq.get("job") != job_name:
		frappe.throw(
			_("Sales Quote is linked to Job {0} ({1}). It must match the current job.").format(
				sq.get("job") or "", sq.get("job_type") or ""
			)
		)

	quote_field, child_doctype, charge_doctype = JOB_QUOTE_MAP.get(job_doctype, (None, None, None))
	if not quote_field:
		frappe.throw(_("Get Additional Charges is not supported for {0}.").format(job_doctype))

	job_doc = frappe.get_doc(job_doctype, job_name)
	charges_field = _get_charges_field(job_doctype)
	if not charges_field or not hasattr(job_doc, charges_field):
		frappe.throw(_("Job has no charges table."))

	# Load quote child rows
	child_rows = frappe.get_all(
		child_doctype,
		filters={"parent": sales_quote_name, "parenttype": "Sales Quote"},
		fields=["*"],
		order_by="idx",
	)
	if not child_rows:
		return {"success": False, "message": _("No charge items in this Sales Quote."), "charges_added": 0}

	# Map quote row to job charge row and set sales_quote_link
	existing = list(getattr(job_doc, charges_field) or [])
	added = 0
	for row in child_rows:
		charge_row = _map_quote_row_to_job_charge(
			job_doctype, charge_doctype, row, sales_quote_name
		)
		if charge_row:
			job_doc.append(charges_field, charge_row)
			added += 1

	if added > 0:
		job_doc.flags.ignore_validate_update_after_submit = True
		job_doc.save(ignore_permissions=True)
	return {
		"success": True,
		"message": _("Added {0} charge(s) from Sales Quote.").format(added),
		"charges_added": added,
	}


def _get_charges_field(job_doctype):
	"""Return the fieldname of the charges table on the job doctype."""
	return "charges"


def _map_quote_row_to_job_charge(job_doctype, charge_doctype, row, sales_quote_name):
	"""Build one job charge row from a Sales Quote child row; set sales_quote_link."""
	common = {"sales_quote_link": sales_quote_name}
	if charge_doctype == "Transport Job Charges":
		return {
			**common,
			"item_code": row.get("item_code"),
			"item_name": row.get("item_name"),
			"quantity": flt(row.get("quantity"), 2),
			"uom": row.get("uom"),
			"currency": row.get("currency"),
			"unit_rate": flt(row.get("unit_rate"), 2),
			"estimated_revenue": flt(row.get("estimated_revenue"), 2),
			"calculation_method": row.get("calculation_method"),
			"cost_quantity": flt(row.get("cost_quantity"), 2),
			"cost_uom": row.get("cost_uom"),
			"cost_currency": row.get("cost_currency"),
			"unit_cost": flt(row.get("unit_cost"), 2),
			"estimated_cost": flt(row.get("estimated_cost"), 2),
			"cost_calculation_method": row.get("cost_calculation_method"),
		}
	if charge_doctype == "Warehouse Job Charges":
		return {
			**common,
			"item_code": row.get("item") or row.get("item_code"),
			"item_name": row.get("item_name"),
			"quantity": flt(row.get("quantity"), 2),
			"uom": row.get("uom"),
			"currency": row.get("selling_currency") or row.get("currency"),
			"rate": flt(row.get("unit_rate"), 2),
			"total": flt(row.get("quantity"), 2) * flt(row.get("unit_rate"), 2),
		}
	if charge_doctype == "Air Shipment Charges":
		return {
			**common,
			"item_code": row.get("item_code"),
			"item_name": row.get("item_name"),
			"quantity": flt(row.get("quantity"), 2),
			"unit_of_measure": row.get("uom"),
			"currency": row.get("currency"),
			"rate": flt(row.get("unit_rate"), 2),
			"estimated_revenue": flt(row.get("estimated_revenue"), 2),
			"estimated_cost": flt(row.get("estimated_cost"), 2),
		}
	if charge_doctype == "Sea Freight Charges":
		return {
			**common,
			"charge_item": row.get("item_code"),
			"charge_name": row.get("item_name"),
			"selling_currency": row.get("currency"),
			"selling_amount": flt(row.get("estimated_revenue"), 2),
			"buying_currency": row.get("cost_currency"),
			"buying_amount": flt(row.get("estimated_cost"), 2),
		}
	return None
