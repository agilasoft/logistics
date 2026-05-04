# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Resolve Internal Job Detail rows on Special Project to operational logistics documents."""

from __future__ import unicode_literals

import frappe

from logistics.utils.charge_service_type import effective_internal_job_detail_job_type


def resolve_internal_job_detail_row_to_operational_ref(row):
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
	if not jn:
		return None
	jt = (getattr(row, "job_type", None) or "").strip() or effective_internal_job_detail_job_type(row)

	if jt == "Air Booking":
		ship = frappe.db.get_value("Air Shipment", {"air_booking": jn}, "name")
		if ship:
			return ("Air Shipment", ship)
	elif jt == "Sea Booking":
		ship = frappe.db.get_value("Sea Shipment", {"sea_booking": jn}, "name")
		if ship:
			return ("Sea Shipment", ship)
	elif jt == "Transport Order":
		tj = frappe.db.get_value("Transport Job", {"transport_order": jn}, "name")
		if tj:
			return ("Transport Job", tj)
	elif jt == "Declaration Order":
		dec = frappe.db.get_value("Declaration", {"declaration_order": jn}, "name")
		if dec:
			return ("Declaration", dec)
	elif jt == "Inbound Order":
		wj = frappe.db.sql(
			"""
			SELECT name FROM `tabWarehouse Job`
			WHERE reference_order = %s AND IFNULL(reference_order_type,'') = 'Inbound Order'
			LIMIT 1
			""",
			(jn,),
		)
		if wj:
			return ("Warehouse Job", wj[0][0])
	elif jt == "Release Order":
		wj = frappe.db.sql(
			"""
			SELECT name FROM `tabWarehouse Job`
			WHERE reference_order = %s AND IFNULL(reference_order_type,'') = 'Release Order'
			LIMIT 1
			""",
			(jn,),
		)
		if wj:
			return ("Warehouse Job", wj[0][0])
	elif jt == "Transfer Order":
		wj = frappe.db.sql(
			"""
			SELECT name FROM `tabWarehouse Job`
			WHERE reference_order = %s AND IFNULL(reference_order_type,'') = 'Transfer Order'
			LIMIT 1
			""",
			(jn,),
		)
		if wj:
			return ("Warehouse Job", wj[0][0])
	return None


def job_refs_from_internal_job_details(doc):
	"""Build list of ``frappe._dict(job_type=DocType, job=name)`` from Special Project job rows."""
	refs = []
	for row in doc.get("internal_job_details") or []:
		pair = resolve_internal_job_detail_row_to_operational_ref(row)
		if pair:
			refs.append(frappe._dict(job_type=pair[0], job=pair[1]))
	return refs
