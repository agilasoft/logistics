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
		# Store previous status so on_update can detect transition to Approved
		if self.get("__islocal") or not self.name:
			self._prev_status = None
		else:
			self._prev_status = frappe.db.get_value("Change Request", self.name, "status")

	def on_update(self):
		"""When status is set to Approved, push charges to the linked job/shipment."""
		if self.status != "Approved" or not self.charges:
			return
		prev = getattr(self, "_prev_status", None)
		if prev == "Approved":
			return
		apply_charges_to_job(self)


def _charge_row_for_air_shipment(row, _job_doc):
	"""Map Change Request Charge to Air Shipment Charges row."""
	return {
		"item_code": row.item_code,
		"charge_type": "Revenue",
		"charge_category": "Other",
		"charge_basis": "Fixed Amount",
		"quantity": flt(row.quantity, 2) or 1,
		"uom": row.uom,
		"currency": row.currency,
		"rate": flt(row.unit_cost, 2),
		"estimated_revenue": flt(row.amount, 2),
		"description": row.description or "",
	}


def _charge_row_for_transport_job(row, _job_doc):
	"""Map Change Request Charge to Transport Job Charges row."""
	return {
		"item_code": row.item_code,
		"charge_type": "Revenue",
		"charge_category": "Other",
		"charge_basis": "Fixed Amount",
		"quantity": flt(row.quantity, 2) or 1,
		"uom": row.uom,
		"currency": row.currency,
		"rate": flt(row.unit_cost, 2),
		"estimated_revenue": flt(row.amount, 2),
		"description": getattr(row, "description", None) or "",
	}


def _charge_row_for_warehouse_job(row, _job_doc):
	"""Map Change Request Charge to Warehouse Job Charges row."""
	return {
		"item_code": row.item_code,
		"charge_type": "Revenue",
		"charge_category": "Other",
		"quantity": flt(row.quantity, 2) or 1,
		"uom": row.uom,
		"currency": row.currency,
		"rate": flt(row.unit_cost, 2),
		"estimated_revenue": flt(row.amount, 2),
	}


def _charge_row_for_sea_shipment(row, job_doc):
	"""Map Change Request Charge to Sea Freight Charges row (Sea Shipment)."""
	# Sea Freight Charges may use charge_item/selling_amount or item_code/rate; try common names
	item_name = ""
	if row.item_code:
		item_name = frappe.db.get_value("Item", row.item_code, "item_name") or ""
	return {
		"item_code": row.item_code,
		"charge_type": "Revenue",
		"charge_category": "Other",
		"charge_basis": "Fixed Amount",
		"quantity": flt(row.quantity, 2) or 1,
		"uom": row.uom,
		"currency": row.currency,
		"rate": flt(row.unit_cost, 2),
		"estimated_revenue": flt(row.amount, 2),
		"description": getattr(row, "description", None) or item_name,
	}


def _charge_row_for_declaration(row, _job_doc):
	"""Map Change Request Charge to Declaration Charges row."""
	return {
		"item_code": row.item_code,
		"calculation_method": "Fixed Amount",
		"quantity": flt(row.quantity, 2) or 1,
		"uom": row.uom,
		"currency": row.currency,
		"unit_rate": flt(row.unit_cost, 2),
		"estimated_revenue": flt(row.amount, 2),
	}


def apply_charges_to_job(cr):
	"""Append Change Request charges to the linked job/shipment. Called when CR is approved."""
	if not cr.job_type or not cr.job or not cr.charges:
		return
	if not frappe.db.exists(cr.job_type, cr.job):
		frappe.throw(_("Job {0} does not exist").format(cr.job))
	job_doc = frappe.get_doc(cr.job_type, cr.job)
	mappers = {
		"Air Shipment": _charge_row_for_air_shipment,
		"Transport Job": _charge_row_for_transport_job,
		"Warehouse Job": _charge_row_for_warehouse_job,
		"Sea Shipment": _charge_row_for_sea_shipment,
		"Declaration": _charge_row_for_declaration,
	}
	mapper = mappers.get(cr.job_type)
	if not mapper:
		frappe.msgprint(
			_("Apply charges to job is not implemented for job type {0}. Charges were not applied.").format(cr.job_type),
			indicator="orange",
		)
		return
	added = 0
	for row in cr.charges:
		if not getattr(row, "item_code", None):
			continue
		charge_data = mapper(row, job_doc)
		if charge_data:
			job_doc.append("charges", charge_data)
			added += 1
	if added > 0:
		job_doc.flags.ignore_validate_update_after_submit = True
		job_doc.save(ignore_permissions=True)
		frappe.msgprint(
			_("Applied {0} charge(s) from Change Request to {1}.").format(added, cr.job),
			indicator="green",
		)


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
