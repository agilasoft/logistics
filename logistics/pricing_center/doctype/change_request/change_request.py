# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document


_SKIP_CHARGE_COPY = frozenset(
	{
		"name",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"docstatus",
		"parent",
		"parentfield",
		"parenttype",
		"idx",
	}
)


class ChangeRequest(Document):
	def on_submit(self):
		from logistics.pricing_center.change_request_to_job import apply_change_request_charges_to_job

		apply_change_request_charges_to_job(self)
		frappe.db.set_value("Change Request", self.name, "status", "Submitted", update_modified=False)

	def on_cancel(self):
		from logistics.pricing_center.change_request_to_job import remove_change_request_charges_from_job

		remove_change_request_charges_from_job(self)
		frappe.db.set_value("Change Request", self.name, "status", "Draft", update_modified=False)


def _charge_row_as_sales_quote_dict(charge_row, default_service_type):
	"""Map Change Request Charge row to Sales Quote Charge child dict (same field names)."""
	out = {}
	for k, v in charge_row.as_dict().items():
		if k in _SKIP_CHARGE_COPY:
			continue
		if v is None or v == "":
			continue
		out[k] = v
	if not out.get("service_type"):
		out["service_type"] = default_service_type
	return out


@frappe.whitelist()
def create_change_request(job_type, job_name):
	"""Create a new Change Request linked to the given job. Returns the new doc name."""
	if not job_type or not job_name:
		frappe.throw(_("Job Type and Job are required"))
	# Validate job exists
	if not frappe.db.exists(job_type, job_name):
		frappe.throw(_("Job {0} does not exist").format(job_name))
	cr = frappe.new_doc("Change Request")
	cr.job_type = job_type
	cr.job = job_name
	cr.status = "Draft"
	cr.insert(ignore_permissions=True)
	return cr.name


@frappe.whitelist()
def create_sales_quote_from_change_request(change_request_name):
	"""Create a Sales Quote from a Change Request (Additional Charge, job reference, items from charges)."""
	cr = frappe.get_doc("Change Request", change_request_name)
	if cr.docstatus != 1:
		frappe.throw(_("Submit the Change Request before creating a Sales Quote."))
	if not cr.charges:
		frappe.throw(_("Change Request has no charge items. Add at least one charge before creating Sales Quote."))
	# Create Sales Quote
	sq = frappe.new_doc("Sales Quote")
	sq.additional_charge = 1
	sq.job_type = cr.job_type
	sq.job = cr.job
	# Copy customer from job if possible
	job_doc = frappe.get_doc(cr.job_type, cr.job)
	customer = getattr(job_doc, "customer", None) or getattr(job_doc, "local_customer", None)
	if customer:
		sq.customer = customer
	# Populate main_service and charges based on job_type
	job_to_service = {
		"Transport Job": "Transport",
		"Warehouse Job": "Warehousing",
		"Air Shipment": "Air",
		"Sea Shipment": "Sea",
		"Declaration": "Customs",
		"Declaration Order": "Customs",
	}
	sq.main_service = job_to_service.get(cr.job_type, "Transport")
	# Additional-charge quotes from Change Request are always one-off (and matching naming series).
	sq.quotation_type = "One-off"
	sq.naming_series = "OOQ.#####"
	sq.change_request = cr.name
	for row in cr.charges:
		row_dict = _charge_row_as_sales_quote_dict(row, sq.main_service)
		row_dict["change_request_charge"] = row.name
		sq.append("charges", row_dict)
	sq.flags.ignore_mandatory = True
	sq.insert(ignore_permissions=True)
	# Link back (submitted doc: avoid save(); status/sales_quote are not allow_on_submit)
	frappe.db.set_value(
		"Change Request",
		cr.name,
		{"sales_quote": sq.name, "status": "Sales Quote Created"},
		update_modified=False,
	)
	return sq.name
