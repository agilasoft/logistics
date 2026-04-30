# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Push Change Request charge lines to the linked job (cost) on CR submit; link rows for later Sales Quote revenue merge."""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt

from logistics.pricing_center.additional_charge_to_job import (
	JOB_TYPE_TO_SERVICE,
	_amendment_family_names,
	_row_val,
)


def _job_currency(job_doc):
	return (
		getattr(job_doc, "currency", None)
		or frappe.defaults.get_global_default("currency")
		or frappe.db.get_single_value("Global Defaults", "default_currency")
	)


def _remove_job_charges_for_change_request(job_doc, change_request_name):
	if not job_doc.get("charges"):
		return
	for row in list(job_doc.charges):
		if getattr(row, "change_request", None) == change_request_name:
			job_doc.remove(row)


def _map_cr_charge_to_air_cost(row, cr_name, charge_row_name):
	qty = flt(_row_val(row, "cost_quantity"), 2)
	if not qty:
		qty = 1
	rev_qty = flt(_row_val(row, "quantity"), 2) or 1
	ccy = _row_val(row, "currency") or _row_val(row, "cost_currency")
	item_name = _row_val(row, "item_name") or ""
	return {
		"service_type": _row_val(row, "service_type") or "Air",
		"item_code": _row_val(row, "item_code"),
		"charge_type": "Margin",
		"charge_category": _row_val(row, "charge_category") or "Other",
		"revenue_calculation_method": _row_val(row, "calculation_method") or "Flat Rate",
		"quantity": rev_qty,
		"uom": _row_val(row, "uom"),
		"currency": ccy,
		"rate": 0,
		"unit_type": _row_val(row, "unit_type"),
		"minimum_quantity": flt(_row_val(row, "minimum_quantity"), 2),
		"minimum_charge": flt(_row_val(row, "minimum_charge"), 2),
		"maximum_charge": flt(_row_val(row, "maximum_charge"), 2),
		"base_amount": 0,
		"estimated_revenue": 0,
		"bill_to": _row_val(row, "bill_to"),
		"description": item_name,
		"cost_calculation_method": _row_val(row, "cost_calculation_method") or "Flat Rate",
		"cost_quantity": qty,
		"cost_uom": _row_val(row, "cost_uom"),
		"cost_currency": _row_val(row, "cost_currency") or ccy,
		"unit_cost": flt(_row_val(row, "unit_cost"), 2),
		"cost_unit_type": _row_val(row, "cost_unit_type"),
		"cost_minimum_quantity": flt(_row_val(row, "cost_minimum_quantity"), 2),
		"cost_minimum_charge": flt(_row_val(row, "cost_minimum_charge"), 2),
		"cost_maximum_charge": flt(_row_val(row, "cost_maximum_charge"), 2),
		"cost_base_amount": flt(_row_val(row, "cost_base_amount"), 2),
		"estimated_cost": flt(_row_val(row, "estimated_cost"), 2),
		"pay_to": _row_val(row, "pay_to"),
		"revenue_calc_notes": "",
		"cost_calc_notes": _row_val(row, "cost_calc_notes") or "",
		"change_request": cr_name,
		"change_request_charge": charge_row_name,
	}


def _map_cr_charge_to_transport_cost(row, cr_name, charge_row_name):
	qty = flt(_row_val(row, "cost_quantity"), 2)
	if not qty:
		qty = 1
	rev_qty = flt(_row_val(row, "quantity"), 2) or 1
	ccy = _row_val(row, "currency") or _row_val(row, "cost_currency")
	return {
		"service_type": _row_val(row, "service_type") or "Transport",
		"item_code": _row_val(row, "item_code"),
		"charge_type": "Margin",
		"charge_category": _row_val(row, "charge_category") or "Other",
		"revenue_calculation_method": _row_val(row, "calculation_method") or "Flat Rate",
		"quantity": rev_qty,
		"uom": _row_val(row, "uom"),
		"currency": ccy,
		"rate": 0,
		"unit_type": _row_val(row, "unit_type"),
		"minimum_quantity": flt(_row_val(row, "minimum_quantity"), 2),
		"minimum_charge": flt(_row_val(row, "minimum_charge"), 2),
		"maximum_charge": flt(_row_val(row, "maximum_charge"), 2),
		"base_amount": 0,
		"estimated_revenue": 0,
		"bill_to": _row_val(row, "bill_to"),
		"cost_calculation_method": _row_val(row, "cost_calculation_method") or "Flat Rate",
		"cost_quantity": qty,
		"cost_uom": _row_val(row, "cost_uom"),
		"cost_currency": _row_val(row, "cost_currency") or ccy,
		"unit_cost": flt(_row_val(row, "unit_cost"), 2),
		"cost_unit_type": _row_val(row, "cost_unit_type"),
		"cost_minimum_quantity": flt(_row_val(row, "cost_minimum_quantity"), 2),
		"cost_minimum_charge": flt(_row_val(row, "cost_minimum_charge"), 2),
		"cost_maximum_charge": flt(_row_val(row, "cost_maximum_charge"), 2),
		"cost_base_amount": flt(_row_val(row, "cost_base_amount"), 2),
		"estimated_cost": flt(_row_val(row, "estimated_cost"), 2),
		"pay_to": _row_val(row, "pay_to"),
		"revenue_calc_notes": "",
		"cost_calc_notes": _row_val(row, "cost_calc_notes") or "",
		"change_request": cr_name,
		"change_request_charge": charge_row_name,
	}


def _map_cr_charge_to_warehouse_cost(row, cr_name, charge_row_name, job_doc):
	ccy = _row_val(row, "currency") or _row_val(row, "cost_currency") or _job_currency(job_doc)
	rev_qty = flt(_row_val(row, "quantity"), 2) or 1
	return {
		"item_code": _row_val(row, "item_code"),
		"charge_type": "Margin",
		"charge_category": _row_val(row, "charge_category") or "Other",
		"service_type": "Warehousing",
		"quantity": rev_qty,
		"uom": _row_val(row, "uom") or _row_val(row, "cost_uom"),
		"currency": ccy,
		"rate": 0,
		"estimated_revenue": 0,
		"estimated_cost": flt(_row_val(row, "estimated_cost"), 2),
		"change_request": cr_name,
		"change_request_charge": charge_row_name,
	}


def _map_cr_charge_to_sea_cost(row, cr_name, charge_row_name):
	qty = flt(_row_val(row, "cost_quantity"), 2)
	if not qty:
		qty = 1
	rev_qty = flt(_row_val(row, "quantity"), 2) or 1
	ccy = _row_val(row, "currency") or _row_val(row, "cost_currency")
	ic = _row_val(row, "item_code")
	item_name = ""
	if ic:
		item_name = frappe.db.get_value("Item", ic, "item_name") or ""
	return {
		"service_type": _row_val(row, "service_type") or "Sea",
		"item_code": ic,
		"charge_type": "Margin",
		"charge_category": _row_val(row, "charge_category") or "Other",
		"revenue_calculation_method": _row_val(row, "calculation_method") or "Flat Rate",
		"quantity": rev_qty,
		"uom": _row_val(row, "uom"),
		"currency": ccy,
		"selling_currency": ccy,
		"buying_currency": _row_val(row, "cost_currency") or ccy,
		"rate": 0,
		"unit_type": _row_val(row, "unit_type"),
		"minimum_quantity": flt(_row_val(row, "minimum_quantity"), 2),
		"minimum_charge": flt(_row_val(row, "minimum_charge"), 2),
		"maximum_charge": flt(_row_val(row, "maximum_charge"), 2),
		"base_amount": 0,
		"estimated_revenue": 0,
		"bill_to": _row_val(row, "bill_to"),
		"description": item_name,
		"cost_calculation_method": _row_val(row, "cost_calculation_method") or "Flat Rate",
		"cost_quantity": qty,
		"cost_uom": _row_val(row, "cost_uom"),
		"cost_currency": _row_val(row, "cost_currency") or ccy,
		"unit_cost": flt(_row_val(row, "unit_cost"), 2),
		"cost_unit_type": _row_val(row, "cost_unit_type"),
		"cost_minimum_quantity": flt(_row_val(row, "cost_minimum_quantity"), 2),
		"cost_minimum_charge": flt(_row_val(row, "cost_minimum_charge"), 2),
		"cost_maximum_charge": flt(_row_val(row, "cost_maximum_charge"), 2),
		"cost_base_amount": flt(_row_val(row, "cost_base_amount"), 2),
		"estimated_cost": flt(_row_val(row, "estimated_cost"), 2),
		"pay_to": _row_val(row, "pay_to"),
		"revenue_calc_notes": "",
		"cost_calc_notes": _row_val(row, "cost_calc_notes") or "",
		"change_request": cr_name,
		"change_request_charge": charge_row_name,
	}


def _map_cr_charge_to_declaration_cost(row, cr_name, charge_row_name):
	qty = flt(_row_val(row, "cost_quantity"), 2)
	if not qty:
		qty = 1
	rev_qty = flt(_row_val(row, "quantity"), 2) or 1
	ccy = _row_val(row, "currency") or _row_val(row, "cost_currency")
	rev_method = _row_val(row, "calculation_method") or "Fixed Amount"
	cost_method = _row_val(row, "cost_calculation_method") or "Fixed Amount"
	return {
		"service_type": "Custom",
		"item_code": _row_val(row, "item_code"),
		"charge_type": "Margin",
		"charge_category": _row_val(row, "charge_category") or "Other",
		"revenue_calculation_method": rev_method,
		"quantity": rev_qty,
		"uom": _row_val(row, "uom"),
		"currency": ccy,
		"selling_currency": ccy,
		"buying_currency": _row_val(row, "cost_currency") or ccy,
		"rate": 0,
		"unit_type": _row_val(row, "unit_type"),
		"minimum_quantity": flt(_row_val(row, "minimum_quantity"), 2),
		"minimum_charge": flt(_row_val(row, "minimum_charge"), 2),
		"maximum_charge": flt(_row_val(row, "maximum_charge"), 2),
		"base_amount": 0,
		"estimated_revenue": 0,
		"bill_to": _row_val(row, "bill_to"),
		"charge_description": _row_val(row, "item_name") or "",
		"cost_calculation_method": cost_method,
		"cost_quantity": qty,
		"cost_uom": _row_val(row, "cost_uom"),
		"cost_currency": _row_val(row, "cost_currency") or ccy,
		"unit_cost": flt(_row_val(row, "unit_cost"), 2),
		"cost_unit_type": _row_val(row, "cost_unit_type"),
		"cost_minimum_quantity": flt(_row_val(row, "cost_minimum_quantity"), 2),
		"cost_minimum_charge": flt(_row_val(row, "cost_minimum_charge"), 2),
		"cost_maximum_charge": flt(_row_val(row, "cost_maximum_charge"), 2),
		"cost_base_amount": flt(_row_val(row, "cost_base_amount"), 2),
		"estimated_cost": flt(_row_val(row, "estimated_cost"), 2),
		"pay_to": _row_val(row, "pay_to"),
		"revenue_calc_notes": "",
		"cost_calc_notes": _row_val(row, "cost_calc_notes") or "",
		"change_request": cr_name,
		"change_request_charge": charge_row_name,
	}


def _cost_mappers():
	return {
		"Air Shipment": _map_cr_charge_to_air_cost,
		"Transport Job": _map_cr_charge_to_transport_cost,
		"Warehouse Job": _map_cr_charge_to_warehouse_cost,
		"Sea Shipment": _map_cr_charge_to_sea_cost,
		"Declaration": _map_cr_charge_to_declaration_cost,
		"Declaration Order": _map_cr_charge_to_declaration_cost,
	}


def apply_change_request_charges_to_job(cr_doc):
	"""On Change Request submit: replace prior lines for this CR on the job, append cost-populated charge rows."""
	if not getattr(cr_doc, "job_type", None) or not getattr(cr_doc, "job", None):
		return
	if not frappe.db.exists(cr_doc.job_type, cr_doc.job):
		frappe.throw(_("Job {0} does not exist").format(cr_doc.job))
	if not cr_doc.get("charges"):
		frappe.msgprint(_("No charge lines on this Change Request; nothing was applied to the job."), indicator="orange")
		return

	expected_service = JOB_TYPE_TO_SERVICE.get(cr_doc.job_type)
	if not expected_service:
		frappe.msgprint(
			_("Change Request job type {0} is not configured for applying charges.").format(cr_doc.job_type),
			indicator="orange",
		)
		return

	mapper_fn = _cost_mappers().get(cr_doc.job_type)
	if not mapper_fn:
		return

	job_doc = frappe.get_doc(cr_doc.job_type, cr_doc.job)
	_remove_job_charges_for_change_request(job_doc, cr_doc.name)

	added = 0
	for row in cr_doc.charges:
		if not _row_val(row, "item_code"):
			continue
		st = _row_val(row, "service_type")
		if st and st != expected_service:
			continue
		if cr_doc.job_type == "Warehouse Job":
			charge_data = mapper_fn(row, cr_doc.name, row.name, job_doc)
		else:
			charge_data = mapper_fn(row, cr_doc.name, row.name)
		if charge_data:
			job_doc.append("charges", charge_data)
			added += 1

	if added > 0:
		job_doc.flags.ignore_validate_update_after_submit = True
		job_doc.save(ignore_permissions=True)
		frappe.msgprint(
			_("Added {0} cost charge line(s) from Change Request {1} to {2}.").format(added, cr_doc.name, cr_doc.job),
			indicator="green",
		)


def remove_change_request_charges_from_job(cr_doc):
	"""On Change Request cancel: remove job lines created from this Change Request."""
	if not getattr(cr_doc, "job_type", None) or not getattr(cr_doc, "job", None):
		return
	if not frappe.db.exists(cr_doc.job_type, cr_doc.job):
		return
	job_doc = frappe.get_doc(cr_doc.job_type, cr_doc.job)
	_remove_job_charges_for_change_request(job_doc, cr_doc.name)
	job_doc.flags.ignore_validate_update_after_submit = True
	job_doc.save(ignore_permissions=True)


def _find_change_request_job_row(job_doc, cr_name, charge_row_name):
	for row in job_doc.get("charges") or []:
		if getattr(row, "change_request", None) == cr_name and getattr(row, "change_request_charge", None) == charge_row_name:
			return row
	return None


def _apply_sq_revenue_to_air_job_row(job_row, sq_row):
	job_row.revenue_calculation_method = _row_val(sq_row, "calculation_method") or "Flat Rate"
	job_row.quantity = flt(_row_val(sq_row, "quantity"), 2) or 1
	job_row.uom = _row_val(sq_row, "uom")
	job_row.currency = _row_val(sq_row, "currency")
	job_row.rate = flt(_row_val(sq_row, "unit_rate"), 2)
	job_row.unit_type = _row_val(sq_row, "unit_type")
	job_row.minimum_quantity = flt(_row_val(sq_row, "minimum_quantity"), 2)
	job_row.minimum_charge = flt(_row_val(sq_row, "minimum_charge"), 2)
	job_row.maximum_charge = flt(_row_val(sq_row, "maximum_charge"), 2)
	job_row.base_amount = flt(_row_val(sq_row, "base_amount"), 2)
	job_row.estimated_revenue = flt(_row_val(sq_row, "estimated_revenue"), 2)
	job_row.bill_to = _row_val(sq_row, "bill_to")
	job_row.revenue_calc_notes = _row_val(sq_row, "revenue_calc_notes") or ""
	job_row.description = _row_val(sq_row, "item_name") or job_row.description


def _apply_sq_revenue_to_transport_job_row(job_row, sq_row):
	job_row.revenue_calculation_method = _row_val(sq_row, "calculation_method") or "Flat Rate"
	job_row.quantity = flt(_row_val(sq_row, "quantity"), 2) or 1
	job_row.uom = _row_val(sq_row, "uom")
	job_row.currency = _row_val(sq_row, "currency")
	if hasattr(job_row, "selling_currency"):
		job_row.selling_currency = _row_val(sq_row, "currency")
	job_row.rate = flt(_row_val(sq_row, "unit_rate"), 2)
	job_row.unit_type = _row_val(sq_row, "unit_type")
	job_row.minimum_quantity = flt(_row_val(sq_row, "minimum_quantity"), 2)
	job_row.minimum_charge = flt(_row_val(sq_row, "minimum_charge"), 2)
	job_row.maximum_charge = flt(_row_val(sq_row, "maximum_charge"), 2)
	job_row.base_amount = flt(_row_val(sq_row, "base_amount"), 2)
	job_row.estimated_revenue = flt(_row_val(sq_row, "estimated_revenue"), 2)
	job_row.bill_to = _row_val(sq_row, "bill_to")
	job_row.revenue_calc_notes = _row_val(sq_row, "revenue_calc_notes") or ""
	ic = _row_val(sq_row, "item_code")
	if ic:
		job_row.description = frappe.db.get_value("Item", ic, "item_name") or job_row.description


def _apply_sq_revenue_to_warehouse_job_row(job_row, sq_row):
	job_row.quantity = flt(_row_val(sq_row, "quantity"), 2) or 1
	job_row.uom = _row_val(sq_row, "uom")
	job_row.currency = _row_val(sq_row, "currency")
	job_row.rate = flt(_row_val(sq_row, "unit_rate"), 2)
	job_row.estimated_revenue = flt(_row_val(sq_row, "estimated_revenue"), 2)
	if hasattr(job_row, "bill_to"):
		job_row.bill_to = _row_val(sq_row, "bill_to")


def _apply_sq_revenue_to_sea_job_row(job_row, sq_row):
	job_row.revenue_calculation_method = _row_val(sq_row, "calculation_method") or "Flat Rate"
	job_row.quantity = flt(_row_val(sq_row, "quantity"), 2) or 1
	job_row.uom = _row_val(sq_row, "uom")
	job_row.currency = _row_val(sq_row, "currency")
	if hasattr(job_row, "selling_currency"):
		job_row.selling_currency = _row_val(sq_row, "currency")
	job_row.rate = flt(_row_val(sq_row, "unit_rate"), 2)
	job_row.unit_type = _row_val(sq_row, "unit_type")
	job_row.minimum_quantity = flt(_row_val(sq_row, "minimum_quantity"), 2)
	job_row.minimum_charge = flt(_row_val(sq_row, "minimum_charge"), 2)
	job_row.maximum_charge = flt(_row_val(sq_row, "maximum_charge"), 2)
	job_row.base_amount = flt(_row_val(sq_row, "base_amount"), 2)
	job_row.estimated_revenue = flt(_row_val(sq_row, "estimated_revenue"), 2)
	job_row.bill_to = _row_val(sq_row, "bill_to")
	job_row.revenue_calc_notes = _row_val(sq_row, "revenue_calc_notes") or ""
	ic = _row_val(sq_row, "item_code")
	if ic:
		job_row.description = frappe.db.get_value("Item", ic, "item_name") or job_row.description


def _apply_sq_revenue_to_declaration_job_row(job_row, sq_row):
	job_row.revenue_calculation_method = _row_val(sq_row, "calculation_method") or "Fixed Amount"
	job_row.quantity = flt(_row_val(sq_row, "quantity"), 2) or 1
	job_row.uom = _row_val(sq_row, "uom")
	job_row.currency = _row_val(sq_row, "currency")
	if hasattr(job_row, "selling_currency"):
		job_row.selling_currency = _row_val(sq_row, "currency")
	job_row.rate = flt(_row_val(sq_row, "unit_rate"), 2)
	job_row.unit_type = _row_val(sq_row, "unit_type")
	job_row.minimum_quantity = flt(_row_val(sq_row, "minimum_quantity"), 2)
	job_row.minimum_charge = flt(_row_val(sq_row, "minimum_charge"), 2)
	job_row.maximum_charge = flt(_row_val(sq_row, "maximum_charge"), 2)
	job_row.base_amount = flt(_row_val(sq_row, "base_amount"), 2)
	job_row.estimated_revenue = flt(_row_val(sq_row, "estimated_revenue"), 2)
	job_row.bill_to = _row_val(sq_row, "bill_to")
	job_row.revenue_calc_notes = _row_val(sq_row, "revenue_calc_notes") or ""
	job_row.charge_description = _row_val(sq_row, "item_name") or job_row.charge_description


def _revenue_appliers():
	return {
		"Air Shipment": _apply_sq_revenue_to_air_job_row,
		"Transport Job": _apply_sq_revenue_to_transport_job_row,
		"Warehouse Job": _apply_sq_revenue_to_warehouse_job_row,
		"Sea Shipment": _apply_sq_revenue_to_sea_job_row,
		"Declaration": _apply_sq_revenue_to_declaration_job_row,
		"Declaration Order": _apply_sq_revenue_to_declaration_job_row,
	}


def merge_sales_quote_revenue_into_change_request_job_rows(sq_doc):
	"""
	Update existing job charge rows (from Change Request) with revenue from Sales Quote lines.
	Returns the number of job rows updated.
	"""
	cr_name = getattr(sq_doc, "change_request", None)
	if not cr_name:
		return 0
	if not frappe.db.exists("Change Request", cr_name):
		return 0

	job_type = sq_doc.job_type
	applier = _revenue_appliers().get(job_type)
	if not applier:
		return 0

	expected_service = JOB_TYPE_TO_SERVICE.get(job_type)
	if not expected_service:
		return 0

	job_doc = frappe.get_doc(sq_doc.job_type, sq_doc.job)
	updated = 0
	for sq_row in sq_doc.get("charges") or []:
		if not _row_val(sq_row, "item_code"):
			continue
		st = _row_val(sq_row, "service_type")
		if st and st != expected_service:
			continue
		ct = _row_val(sq_row, "charge_type") or "Margin"
		if ct in ("Cost",):
			continue
		crc = _row_val(sq_row, "change_request_charge")
		if not crc:
			continue
		job_row = _find_change_request_job_row(job_doc, cr_name, crc)
		if not job_row:
			continue
		applier(job_row, sq_row)
		job_row.sales_quote_link = sq_doc.name
		updated += 1

	if updated > 0:
		job_doc.flags.ignore_validate_update_after_submit = True
		job_doc.save(ignore_permissions=True)
		frappe.msgprint(
			_("Updated revenue on {0} charge line(s) on {1} from Sales Quote {2}.").format(updated, sq_doc.job, sq_doc.name),
			indicator="green",
		)
	return updated


def clear_sales_quote_revenue_from_change_request_job_rows(sq_doc):
	"""On Sales Quote cancel: strip quote link and revenue from rows tied to this Change Request + quote family."""
	cr_name = getattr(sq_doc, "change_request", None)
	if not cr_name:
		return
	if not frappe.db.exists(sq_doc.job_type, sq_doc.job):
		return

	family = _amendment_family_names(sq_doc)
	job_doc = frappe.get_doc(sq_doc.job_type, sq_doc.job)
	job_type = sq_doc.job_type
	changed = False

	for job_row in job_doc.get("charges") or []:
		if getattr(job_row, "change_request", None) != cr_name:
			continue
		link = getattr(job_row, "sales_quote_link", None)
		if not link or link not in family:
			continue
		job_row.sales_quote_link = None
		if job_type == "Air Shipment":
			job_row.estimated_revenue = 0
			job_row.rate = 0
			job_row.revenue_calc_notes = ""
		elif job_type == "Transport Job":
			job_row.estimated_revenue = 0
			if hasattr(job_row, "rate"):
				job_row.rate = 0
			job_row.revenue_calc_notes = ""
		elif job_type == "Warehouse Job":
			job_row.estimated_revenue = 0
			job_row.rate = 0
		elif job_type == "Sea Shipment":
			job_row.estimated_revenue = 0
			job_row.rate = 0
			job_row.revenue_calc_notes = ""
		elif job_type in ("Declaration", "Declaration Order"):
			job_row.estimated_revenue = 0
			job_row.rate = 0
			job_row.revenue_calc_notes = ""
		changed = True

	if changed:
		job_doc.flags.ignore_validate_update_after_submit = True
		job_doc.save(ignore_permissions=True)
