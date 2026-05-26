# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "exhibit", "label": _("Exhibit"), "fieldtype": "Link", "options": "Exhibit", "width": 160},
		{"fieldname": "lifecycle_stage", "label": _("Stage"), "fieldtype": "Data", "width": 100},
		{"fieldname": "total_activities", "label": _("Total"), "fieldtype": "Int", "width": 70},
		{"fieldname": "completed", "label": _("Completed"), "fieldtype": "Int", "width": 90},
		{"fieldname": "completion_pct", "label": _("Completion %"), "fieldtype": "Percent", "width": 100},
	]
	conditions = ["ep.docstatus < 2"]
	values = {}
	if filters.get("lifecycle_stage"):
		conditions.append("ep.lifecycle_stage = %(lifecycle_stage)s")
		values["lifecycle_stage"] = filters["lifecycle_stage"]
	where = " AND ".join(conditions)
	programs = frappe.db.sql(
		f"SELECT name, lifecycle_stage FROM `tabExhibit` ep WHERE {where}",
		values,
		as_dict=1,
	)
	data = []
	for prog in programs:
		acts = frappe.db.sql(
			"""
			SELECT lifecycle_activity_status AS status
			FROM `tabLifecycle Job`
			WHERE parent = %s AND parenttype = 'Exhibit' AND IFNULL(activity_code, '') != ''
			""",
			prog.name,
			as_dict=True,
		)
		total = len(acts)
		done = sum(1 for a in acts if a.status in ("Completed", "N/A"))
		pct = (done / total * 100) if total else 0
		data.append(
			{
				"exhibit": prog.name,
				"lifecycle_stage": prog.lifecycle_stage,
				"total_activities": total,
				"completed": done,
				"completion_pct": pct,
			}
		)
	return columns, data
