# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class ChangeRequest(Document):
	def validate(self):
		if self.docstatus == 0 and self.charges:
			# Ensure amount is set on child rows
			for row in self.charges:
				if row.quantity is not None and row.unit_cost is not None:
					row.amount = flt(row.quantity, 2) * flt(row.unit_cost, 2)


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
	# Populate transport/warehousing/air/sea based on job_type and add items to the relevant child table
	if cr.job_type == "Transport Job":
		sq.is_transport = 1
		for row in cr.charges:
			sq.append(
				"transport",
				{
					"item_code": row.item_code,
					"quantity": flt(row.quantity, 2),
					"uom": row.uom,
					"currency": row.currency,
					"unit_rate": flt(row.unit_cost, 2),
					"estimated_revenue": flt(row.amount, 2),
				},
			)
	elif cr.job_type == "Warehouse Job":
		sq.is_warehousing = 1
		for row in cr.charges:
			sq.append(
				"warehousing",
				{
					"item": row.item_code,
					"quantity": flt(row.quantity, 2),
					"uom": row.uom,
					"selling_currency": row.currency,
					"unit_rate": flt(row.unit_cost, 2),
				},
			)
	elif cr.job_type == "Air Shipment":
		sq.is_air = 1
		for row in cr.charges:
			sq.append(
				"air_freight",
				{
					"item_code": row.item_code,
					"quantity": flt(row.quantity, 2),
					"uom": row.uom,
					"currency": row.currency,
					"unit_rate": flt(row.unit_cost, 2),
					"estimated_revenue": flt(row.amount, 2),
				},
			)
	elif cr.job_type == "Sea Shipment":
		sq.is_sea = 1
		for row in cr.charges:
			sq.append(
				"sea_freight",
				{
					"item_code": row.item_code,
					"quantity": flt(row.quantity, 2),
					"uom": row.uom,
					"currency": row.currency,
					"unit_rate": flt(row.unit_cost, 2),
					"estimated_revenue": flt(row.amount, 2),
				},
			)
	else:
		# Declaration or other: use transport as fallback for charge items
		sq.is_transport = 1
		for row in cr.charges:
			sq.append(
				"transport",
				{
					"item_code": row.item_code,
					"quantity": flt(row.quantity, 2),
					"uom": row.uom,
					"currency": row.currency,
					"unit_rate": flt(row.unit_cost, 2),
					"estimated_revenue": flt(row.amount, 2),
				},
			)
	sq.flags.ignore_mandatory = True
	sq.insert(ignore_permissions=True)
	# Link back
	cr.sales_quote = sq.name
	cr.status = "Sales Quote Created"
	cr.flags.ignore_permissions = True
	cr.save()
	return sq.name
