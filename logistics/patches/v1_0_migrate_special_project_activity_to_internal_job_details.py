# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Copy legacy Special Project Activity rows into Internal Job Detail (Jobs) after schema change."""

from __future__ import unicode_literals

import frappe


def _finalize_ij_row(out, activity_name):
	"""Preserve legacy activity name in resource notes (Label field removed from Internal Job Detail)."""
	if activity_name and out:
		prev = (out.get("sp_resource_notes") or "").strip()
		out["sp_resource_notes"] = (activity_name + (" — " + prev if prev else "")).strip()
	return out


def _map_activity_to_ij_row(ar):
	"""Build dict for append('internal_job_details', row)."""
	out = {}
	job_type = (ar.get("job_type") or "").strip()
	aname = (ar.get("activity_name") or "").strip()
	for fin in ("planned_cost", "actual_cost", "planned_revenue", "actual_revenue"):
		if ar.get(fin) is not None:
			out[fin] = ar.get(fin)

	lj = (ar.get("logistics_job") or "").strip()
	bo = (ar.get("booking_order") or "").strip()
	bod = (ar.get("booking_order_doctype") or "").strip()
	spj = (ar.get("special_project_job") or "").strip()

	if job_type == "Project Task Job":
		out["service_type"] = "Special Project"
		out["job_no"] = spj
		if ar.get("equipment_type"):
			out["sp_equipment_type"] = ar.get("equipment_type")
		if ar.get("special_handling"):
			out["sp_handling"] = ar.get("special_handling")
		return _finalize_ij_row(out, aname)

	if lj:
		if job_type == "Air":
			bk = frappe.db.get_value("Air Shipment", lj, "air_booking")
			out["service_type"] = "Air"
			out["job_no"] = bk or lj
		elif job_type == "Sea":
			bk = frappe.db.get_value("Sea Shipment", lj, "sea_booking")
			out["service_type"] = "Sea"
			out["job_no"] = bk or lj
		elif job_type == "Transport":
			to = frappe.db.get_value("Transport Job", lj, "transport_order")
			out["service_type"] = "Transport"
			out["job_no"] = to or lj
		elif job_type == "Customs":
			do = frappe.db.get_value("Declaration", lj, "declaration_order")
			out["service_type"] = "Customs"
			out["job_no"] = do or lj
		elif job_type == "Warehousing":
			rt = frappe.db.get_value(
				"Warehouse Job",
				lj,
				["reference_order_type", "reference_order"],
				as_dict=True,
			)
			out["service_type"] = "Warehousing"
			if rt and rt.get("reference_order"):
				out["job_no"] = rt.get("reference_order")
				jt = (rt.get("reference_order_type") or "").strip()
				if jt in ("Inbound Order", "Release Order", "Transfer Order"):
					out["job_type"] = jt
			else:
				out["job_no"] = lj
		return _finalize_ij_row(out, aname)

	if bo and bod:
		st_map = {
			"Inbound Order": "Warehousing",
			"Release Order": "Warehousing",
			"Transfer Order": "Warehousing",
			"Transport Order": "Transport",
			"Air Booking": "Air",
			"Sea Booking": "Sea",
		}
		st = st_map.get(bod)
		if st:
			out["service_type"] = st
			out["job_no"] = bo
			if bod in ("Inbound Order", "Release Order", "Transfer Order"):
				out["job_type"] = bod

	return _finalize_ij_row(out, aname)


def execute():
	if not frappe.db.table_exists("tabSpecial Project Activity"):
		return

	rows = frappe.db.sql(
		"""
		SELECT * FROM `tabSpecial Project Activity`
		WHERE parenttype = 'Special Project'
			AND IFNULL(parentfield, '') = 'activity'
		ORDER BY parent, idx ASC
		""",
		as_dict=True,
	)
	if not rows:
		return

	by_parent = {}
	for r in rows:
		by_parent.setdefault(r.parent, []).append(r)

	for parent, act_rows in by_parent.items():
		if not frappe.db.exists("Special Project", parent):
			continue
		existing = frappe.db.count(
			"Internal Job Detail",
			{
				"parent": parent,
				"parenttype": "Special Project",
				"parentfield": "internal_job_details",
			},
		)
		if existing:
			continue

		sp = frappe.get_doc("Special Project", parent)
		for ar in act_rows:
			payload = _map_activity_to_ij_row(ar)
			if payload:
				sp.append("internal_job_details", payload)
		sp.save(ignore_permissions=True)

	frappe.db.commit()
