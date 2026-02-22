# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _

# Pipeline stages in order
PIPELINE_ORDER = ["Draft", "Scoping", "Booked", "Planning", "Approved", "In Progress", "On Hold", "Completed", "Cancelled"]


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "status", "label": _("Stage"), "fieldtype": "Data", "width": 120},
		{"fieldname": "project_count", "label": _("Count"), "fieldtype": "Int", "width": 90},
		{"fieldname": "projects", "label": _("Projects"), "fieldtype": "Data", "width": 400},
	]


def get_data(filters):
	conditions = ["1=1"]
	values = {}

	if filters.get("customer"):
		conditions.append("sp.customer = %(customer)s")
		values["customer"] = filters["customer"]
	if filters.get("priority"):
		conditions.append("sp.priority = %(priority)s")
		values["priority"] = filters["priority"]
	if not filters.get("include_cancelled"):
		conditions.append("sp.status != 'Cancelled'")

	where = " AND ".join(conditions)

	rows = frappe.db.sql(
		"""
		SELECT sp.status, sp.name
		FROM `tabSpecial Project` sp
		WHERE {where}
		ORDER BY FIELD(sp.status, 'Draft', 'Scoping', 'Booked', 'Planning', 'Approved', 'In Progress', 'On Hold', 'Completed', 'Cancelled'), sp.modified DESC
		""".format(where=where),
		values,
		as_dict=1,
	)

	# Group by status
	by_status = {}
	for r in rows:
		s = r["status"] or "Draft"
		if s not in by_status:
			by_status[s] = []
		by_status[s].append(r["name"])

	# Build result in pipeline order
	result = []
	for status in PIPELINE_ORDER:
		if status in by_status:
			names = by_status[status]
			result.append({
				"status": status,
				"project_count": len(names),
				"projects": ", ".join(names[:10]) + ("..." if len(names) > 10 else ""),
			})

	return result
