# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Resolve Lifecycle Job rows on Special Project to operational logistics documents.

The helpers historically named ``*_internal_job_details`` now operate on the
``lifecycle_jobs`` table backed by the ``Lifecycle Job`` child DocType. The old
function names are preserved as aliases for backward compatibility.
"""

from __future__ import unicode_literals

import frappe

from logistics.utils.charge_service_type import effective_internal_job_detail_job_type

_EXECUTION_DOCTYPES = frozenset(
	{
		"Air Shipment",
		"Sea Shipment",
		"Transport Job",
		"Declaration",
		"Warehouse Job",
		"Project Job",
	}
)


def _resolve_order_ref_to_operational_ref(order_type: str, order_no: str):
	"""Resolve a planning booking/order to its submitted shipment/job, if any."""
	order_type = (order_type or "").strip()
	order_no = (order_no or "").strip()
	if not order_type or not order_no:
		return None

	if order_type == "Air Booking":
		ship = frappe.db.get_value("Air Shipment", {"air_booking": order_no}, "name")
		if ship:
			return ("Air Shipment", ship)
	elif order_type == "Sea Booking":
		ship = frappe.db.get_value("Sea Shipment", {"sea_booking": order_no}, "name")
		if ship:
			return ("Sea Shipment", ship)
	elif order_type == "Transport Order":
		tj = frappe.db.get_value("Transport Job", {"transport_order": order_no}, "name")
		if tj:
			return ("Transport Job", tj)
	elif order_type == "Declaration Order":
		dec = frappe.db.get_value("Declaration", {"declaration_order": order_no}, "name")
		if dec:
			return ("Declaration", dec)
	elif order_type == "Inbound Order":
		wj = frappe.db.sql(
			"""
			SELECT name FROM `tabWarehouse Job`
			WHERE reference_order = %s AND IFNULL(reference_order_type,'') = 'Inbound Order'
			LIMIT 1
			""",
			(order_no,),
		)
		if wj:
			return ("Warehouse Job", wj[0][0])
	elif order_type == "Release Order":
		wj = frappe.db.sql(
			"""
			SELECT name FROM `tabWarehouse Job`
			WHERE reference_order = %s AND IFNULL(reference_order_type,'') = 'Release Order'
			LIMIT 1
			""",
			(order_no,),
		)
		if wj:
			return ("Warehouse Job", wj[0][0])
	elif order_type == "Transfer Order":
		wj = frappe.db.sql(
			"""
			SELECT name FROM `tabWarehouse Job`
			WHERE reference_order = %s AND IFNULL(reference_order_type,'') = 'Transfer Order'
			LIMIT 1
			""",
			(order_no,),
		)
		if wj:
			return ("Warehouse Job", wj[0][0])
	return None


def _resolve_execution_name_to_operational_ref(job_name: str):
	"""Resolve a stored shipment/job name to its operational doctype."""
	job_name = (job_name or "").strip()
	if not job_name:
		return None
	for doctype in _EXECUTION_DOCTYPES:
		if frappe.db.exists(doctype, job_name):
			return (doctype, job_name)
	return None


def resolve_lifecycle_job_row_to_operational_ref(row):
	"""
	Return ``(logistics_doctype, job_name)`` for dashboards and milestones (operational job doc),
	or ``None`` when the row is resource-only (Special Project) or cannot be resolved.
	"""
	if not row:
		return None
	st = (getattr(row, "service_type", None) or "").strip()
	if st == "Special Project":
		return None

	jn = (getattr(row, "job_no", None) or "").strip()
	if jn:
		ref = _resolve_execution_name_to_operational_ref(jn)
		if ref:
			return ref

	jt = (getattr(row, "job_type", None) or "").strip()
	on = (getattr(row, "order_no", None) or "").strip()
	if jt and on:
		ref = _resolve_order_ref_to_operational_ref(jt, on)
		if ref:
			return ref

	ot = (getattr(row, "order_type", None) or "").strip()
	if ot and on:
		ref = _resolve_order_ref_to_operational_ref(ot, on)
		if ref:
			return ref

	mapped = effective_internal_job_detail_job_type(row)
	if mapped and on:
		return _resolve_order_ref_to_operational_ref(mapped, on)
	return None


def job_refs_from_lifecycle_jobs(doc, field_name: str = "lifecycle_jobs"):
	"""Build list of ``frappe._dict(job_type=DocType, job=name)`` from project lifecycle rows."""
	refs = []
	for row in doc.get(field_name) or []:
		pair = resolve_lifecycle_job_row_to_operational_ref(row)
		if pair:
			refs.append(frappe._dict(job_type=pair[0], job=pair[1]))
	return refs


def job_refs_from_special_project_services(doc, field_name: str = "special_project_services"):
	"""Build job refs from Special Project programme service rows."""
	refs = []
	for row in doc.get(field_name) or []:
		pair = resolve_lifecycle_job_row_to_operational_ref(row)
		if pair:
			refs.append(frappe._dict(job_type=pair[0], job=pair[1]))
	return refs


def job_refs_for_special_project(doc):
	"""Operational job refs from programme services, falling back to legacy lifecycle rows."""
	refs = job_refs_from_special_project_services(doc)
	if refs:
		return refs
	return job_refs_from_lifecycle_jobs(doc)


resolve_internal_job_detail_row_to_operational_ref = resolve_lifecycle_job_row_to_operational_ref
job_refs_from_internal_job_details = job_refs_from_lifecycle_jobs
