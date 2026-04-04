# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Apply additional-charge Sales Quote lines to the linked job on submit, with sales_quote_link."""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt


JOB_TYPE_TO_SERVICE = {
	"Transport Job": "Transport",
	"Warehouse Job": "Warehousing",
	"Air Shipment": "Air",
	"Sea Shipment": "Sea",
	"Declaration": "Customs",
	"Declaration Order": "Customs",
}


def _amendment_family_names(sq_doc):
	"""All Sales Quote names in this amendment chain (current + predecessors)."""
	names = {sq_doc.name}
	cur = getattr(sq_doc, "amended_from", None)
	while cur:
		names.add(cur)
		cur = frappe.db.get_value("Sales Quote", cur, "amended_from")
	return names


def _row_val(row, fieldname, default=None):
	if row is None:
		return default
	if isinstance(row, dict):
		return row.get(fieldname, default)
	return getattr(row, fieldname, default)


def _remove_job_charges_for_sales_quote_family(job_doc, sales_quote_names):
	"""Drop charge rows whose sales_quote_link is in the given name set."""
	if not job_doc.get("charges"):
		return
	for row in list(job_doc.charges):
		link = getattr(row, "sales_quote_link", None)
		if link and link in sales_quote_names:
			job_doc.remove(row)


def _map_sq_charge_to_air(row, sales_quote_name):
	qty = flt(_row_val(row, "quantity"), 2) or 1
	return {
		"service_type": _row_val(row, "service_type") or "Air",
		"item_code": _row_val(row, "item_code"),
		"charge_type": "Revenue",
		"charge_category": "Other",
		"revenue_calculation_method": _row_val(row, "calculation_method") or "Flat Rate",
		"quantity": qty,
		"uom": _row_val(row, "uom"),
		"currency": _row_val(row, "currency"),
		"rate": flt(_row_val(row, "unit_rate"), 2),
		"estimated_revenue": flt(_row_val(row, "estimated_revenue"), 2),
		"description": _row_val(row, "item_name") or "",
		"sales_quote_link": sales_quote_name,
	}


def _map_sq_charge_to_transport(row, sales_quote_name):
	qty = flt(_row_val(row, "quantity"), 2) or 1
	return {
		"service_type": _row_val(row, "service_type") or "Transport",
		"item_code": _row_val(row, "item_code"),
		"charge_type": "Revenue",
		"charge_category": "Other",
		"revenue_calculation_method": _row_val(row, "calculation_method") or "Flat Rate",
		"quantity": qty,
		"uom": _row_val(row, "uom"),
		"currency": _row_val(row, "currency"),
		"unit_rate": flt(_row_val(row, "unit_rate"), 2),
		"estimated_revenue": flt(_row_val(row, "estimated_revenue"), 2),
		"description": "",
		"sales_quote_link": sales_quote_name,
	}


def _map_sq_charge_to_warehouse(row, sales_quote_name):
	qty = flt(_row_val(row, "quantity"), 2) or 1
	return {
		"item_code": _row_val(row, "item_code"),
		"charge_type": "Revenue",
		"charge_category": "Other",
		"quantity": qty,
		"uom": _row_val(row, "uom"),
		"currency": _row_val(row, "currency"),
		"rate": flt(_row_val(row, "unit_rate"), 2),
		"estimated_revenue": flt(_row_val(row, "estimated_revenue"), 2),
		"service_type": "Warehousing",
		"sales_quote_link": sales_quote_name,
	}


def _map_sq_charge_to_sea(row, sales_quote_name):
	item_name = ""
	ic = _row_val(row, "item_code")
	if ic:
		item_name = frappe.db.get_value("Item", ic, "item_name") or ""
	qty = flt(_row_val(row, "quantity"), 2) or 1
	return {
		"service_type": _row_val(row, "service_type") or "Sea",
		"item_code": ic,
		"charge_type": "Revenue",
		"charge_category": "Other",
		"revenue_calculation_method": _row_val(row, "calculation_method") or "Flat Rate",
		"quantity": qty,
		"uom": _row_val(row, "uom"),
		"currency": _row_val(row, "currency"),
		"rate": flt(_row_val(row, "unit_rate"), 2),
		"estimated_revenue": flt(_row_val(row, "estimated_revenue"), 2),
		"description": item_name,
		"sales_quote_link": sales_quote_name,
	}


def _map_sq_charge_to_declaration(row, sales_quote_name):
	qty = flt(_row_val(row, "quantity"), 2) or 1
	rev_method = _row_val(row, "calculation_method") or "Fixed Amount"
	return {
		"service_type": "Customs",
		"item_code": _row_val(row, "item_code"),
		"charge_type": "Revenue",
		"charge_category": "Other",
		"revenue_calculation_method": rev_method,
		"quantity": qty,
		"uom": _row_val(row, "uom"),
		"currency": _row_val(row, "currency"),
		"rate": flt(_row_val(row, "unit_rate"), 2),
		"estimated_revenue": flt(_row_val(row, "estimated_revenue"), 2),
		"sales_quote_link": sales_quote_name,
	}


def _mappers():
	return {
		"Air Shipment": _map_sq_charge_to_air,
		"Transport Job": _map_sq_charge_to_transport,
		"Warehouse Job": _map_sq_charge_to_warehouse,
		"Sea Shipment": _map_sq_charge_to_sea,
		"Declaration": _map_sq_charge_to_declaration,
		"Declaration Order": _map_sq_charge_to_declaration,
	}


def apply_additional_charge_sales_quote_to_job(sq_doc):
	"""
	Push Sales Quote Charge rows to the linked job and set sales_quote_link.
	Removes prior job lines for this quote amendment family, then appends fresh lines.
	When linked to a Change Request, updates revenue on job rows created at CR submit (matched by change_request_charge).
	"""
	if not getattr(sq_doc, "additional_charge", 0):
		return
	if not getattr(sq_doc, "job_type", None) or not getattr(sq_doc, "job", None):
		return
	if not frappe.db.exists(sq_doc.job_type, sq_doc.job):
		frappe.throw(_("Job {0} does not exist").format(sq_doc.job))
	if not sq_doc.get("charges"):
		frappe.msgprint(_("No charge lines on this Sales Quote; nothing was applied to the job."), indicator="orange")
		return

	if getattr(sq_doc, "change_request", None):
		from logistics.pricing_center.change_request_to_job import merge_sales_quote_revenue_into_change_request_job_rows

		n_merged = merge_sales_quote_revenue_into_change_request_job_rows(sq_doc)
		if n_merged > 0:
			return
		has_crc = any(_row_val(r, "change_request_charge") for r in sq_doc.get("charges") or [])
		if has_crc:
			frappe.msgprint(
				_(
					"No matching job charge rows for this Change Request. Submit the Change Request first so cost lines are added to the job."
				),
				indicator="orange",
			)
			return

	expected_service = JOB_TYPE_TO_SERVICE.get(sq_doc.job_type)
	if not expected_service:
		frappe.msgprint(
			_("Additional charge application is not configured for job type {0}.").format(sq_doc.job_type),
			indicator="orange",
		)
		return

	mapper = _mappers().get(sq_doc.job_type)
	if not mapper:
		return

	job_doc = frappe.get_doc(sq_doc.job_type, sq_doc.job)
	family = _amendment_family_names(sq_doc)
	_remove_job_charges_for_sales_quote_family(job_doc, family)

	added = 0
	for row in sq_doc.charges:
		if not _row_val(row, "item_code"):
			continue
		st = _row_val(row, "service_type")
		if st and st != expected_service:
			continue
		ct = _row_val(row, "charge_type") or "Margin"
		if ct in ("Cost",):
			continue
		charge_data = mapper(row, sq_doc.name)
		if charge_data:
			job_doc.append("charges", charge_data)
			added += 1

	if added > 0:
		job_doc.flags.ignore_validate_update_after_submit = True
		job_doc.save(ignore_permissions=True)
		frappe.msgprint(
			_("Added {0} charge(s) from Sales Quote {1} to {2}.").format(added, sq_doc.name, sq_doc.job),
			indicator="green",
		)


def remove_additional_charge_sales_quote_from_job(sq_doc):
	"""Remove job charge rows linked to this Sales Quote (e.g. on cancel)."""
	if not getattr(sq_doc, "additional_charge", 0):
		return
	if not getattr(sq_doc, "job_type", None) or not getattr(sq_doc, "job", None):
		return
	if not frappe.db.exists(sq_doc.job_type, sq_doc.job):
		return
	if getattr(sq_doc, "change_request", None):
		from logistics.pricing_center.change_request_to_job import clear_sales_quote_revenue_from_change_request_job_rows

		clear_sales_quote_revenue_from_change_request_job_rows(sq_doc)
		return
	job_doc = frappe.get_doc(sq_doc.job_type, sq_doc.job)
	names = {sq_doc.name}
	_remove_job_charges_for_sales_quote_family(job_doc, names)
	job_doc.flags.ignore_validate_update_after_submit = True
	job_doc.save(ignore_permissions=True)
