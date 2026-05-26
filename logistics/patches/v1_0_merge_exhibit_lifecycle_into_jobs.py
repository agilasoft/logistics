# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Move Exhibit Service Activity rows into Jobs (internal_job_details) and drop child DocType."""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.table_exists("tabExhibit"):
		return

	activity_table = None
	for name in ("tabExhibit Service Activity", "tabEvent Service Activity"):
		if frappe.db.table_exists(name):
			activity_table = name
			break

	if activity_table:
		rows = frappe.db.sql(
			f"""
			SELECT parent, lifecycle_stage, activity_code, activity_name, status,
				linked_job_type, linked_job_no, notes
			FROM `{activity_table}`
			WHERE parenttype = 'Exhibit'
			ORDER BY parent, idx
			""",
			as_dict=True,
		)
		by_parent: dict[str, list] = {}
		for row in rows:
			by_parent.setdefault(row.parent, []).append(row)

		for exhibit_name, activities in by_parent.items():
			if not frappe.db.exists("Exhibit", exhibit_name):
				continue
			doc = frappe.get_doc("Exhibit", exhibit_name)
			existing_codes = {
				(r.activity_code or "").strip()
				for r in doc.get("internal_job_details") or []
				if (r.activity_code or "").strip()
			}
			for act in activities:
				code = (act.activity_code or "").strip()
				if code and code in existing_codes:
					continue
				job_type = _map_linked_job_type(act.linked_job_type)
				doc.append(
					"internal_job_details",
					{
						"service_type": "Exhibits",
						"lifecycle_stage": act.lifecycle_stage,
						"activity_code": act.activity_code,
						"activity_name": act.activity_name,
						"lifecycle_activity_status": act.status or "Not Started",
						"job_description": act.activity_name or act.activity_code,
						"job_type": job_type,
						"job_no": act.linked_job_no if job_type else None,
					},
				)
				if code:
					existing_codes.add(code)
			doc.save(ignore_permissions=True)

	if frappe.db.exists("DocType", "Exhibit Service Activity"):
		frappe.delete_doc("DocType", "Exhibit Service Activity", force=True, ignore_missing=True)

	for table in ("tabExhibit Service Activity", "tabEvent Service Activity"):
		if frappe.db.table_exists(table):
			frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `{table}`")

	frappe.db.commit()
	frappe.clear_cache()


def _map_linked_job_type(linked_job_type: str | None) -> str | None:
	if not linked_job_type:
		return None
	mapping = {
		"Air Booking": "Air Booking",
		"Sea Booking": "Sea Booking",
		"Transport Order": "Transport Order",
		"Declaration Order": "Declaration Order",
		"Inbound Order": "Inbound Order",
		"Release Order": "Release Order",
		"Transfer Order": "Transfer Order",
		"Project Job": "Project Job",
	}
	return mapping.get(linked_job_type.strip())
