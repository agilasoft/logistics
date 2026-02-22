# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_columns(filters):
	group_by = (filters or {}).get("group_by") or "None"
	if group_by == "Customer":
		return [
			{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 150},
			{"fieldname": "project_count", "label": _("Projects"), "fieldtype": "Int", "width": 90},
			{"fieldname": "total_planned_cost", "label": _("Total Planned Cost"), "fieldtype": "Currency", "width": 130},
			{"fieldname": "total_actual_cost", "label": _("Total Actual Cost"), "fieldtype": "Currency", "width": 130},
			{"fieldname": "total_planned_revenue", "label": _("Total Planned Revenue"), "fieldtype": "Currency", "width": 140},
			{"fieldname": "total_actual_revenue", "label": _("Total Actual Revenue"), "fieldtype": "Currency", "width": 140},
			{"fieldname": "total_margin", "label": _("Total Margin"), "fieldtype": "Currency", "width": 120},
			{"fieldname": "margin_pct", "label": _("Margin %"), "fieldtype": "Percent", "width": 90},
		]
	if group_by == "Status":
		return [
			{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 110},
			{"fieldname": "project_count", "label": _("Projects"), "fieldtype": "Int", "width": 90},
			{"fieldname": "total_planned_cost", "label": _("Total Planned Cost"), "fieldtype": "Currency", "width": 130},
			{"fieldname": "total_actual_cost", "label": _("Total Actual Cost"), "fieldtype": "Currency", "width": 130},
			{"fieldname": "total_planned_revenue", "label": _("Total Planned Revenue"), "fieldtype": "Currency", "width": 140},
			{"fieldname": "total_actual_revenue", "label": _("Total Actual Revenue"), "fieldtype": "Currency", "width": 140},
			{"fieldname": "total_margin", "label": _("Total Margin"), "fieldtype": "Currency", "width": 120},
			{"fieldname": "margin_pct", "label": _("Margin %"), "fieldtype": "Percent", "width": 90},
		]
	return [
		{"fieldname": "name", "label": _("Project"), "fieldtype": "Link", "options": "Special Project", "width": 130},
		{"fieldname": "project_name", "label": _("Project Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 150},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 110},
		{"fieldname": "total_planned_cost", "label": _("Planned Cost"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "total_actual_cost", "label": _("Actual Cost"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "total_planned_revenue", "label": _("Planned Revenue"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "total_actual_revenue", "label": _("Actual Revenue"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "total_margin", "label": _("Margin"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "margin_pct", "label": _("Margin %"), "fieldtype": "Percent", "width": 90},
	]


def get_data(filters):
	conditions = ["1=1"]
	values = {}

	if filters.get("from_date"):
		conditions.append("DATE(sp.creation) >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("DATE(sp.creation) <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	if filters.get("customer"):
		conditions.append("sp.customer = %(customer)s")
		values["customer"] = filters["customer"]

	where = " AND ".join(conditions)
	group_by = (filters or {}).get("group_by") or "None"

	if group_by == "Customer":
		rows = frappe.db.sql(
			"""
			SELECT sp.customer,
				COUNT(DISTINCT sp.name) as project_count,
				COALESCE(SUM(j.planned_cost), 0) as total_planned_cost,
				COALESCE(SUM(j.actual_cost), 0) as total_actual_cost,
				COALESCE(SUM(j.planned_revenue), 0) as total_planned_revenue,
				COALESCE(SUM(j.actual_revenue), 0) as total_actual_revenue
			FROM `tabSpecial Project` sp
			LEFT JOIN `tabSpecial Project Job` j ON j.parent = sp.name AND j.parenttype = 'Special Project'
			WHERE {where}
			GROUP BY sp.customer
			ORDER BY total_actual_revenue DESC
			""".format(where=where),
			values,
			as_dict=1,
		)
		for r in rows:
			r["total_margin"] = (r["total_actual_revenue"] or 0) - (r["total_actual_cost"] or 0)
			rev = r["total_actual_revenue"] or 0
			r["margin_pct"] = (r["total_margin"] / rev * 100) if rev else 0
		return rows
	elif group_by == "Status":
		rows = frappe.db.sql(
			"""
			SELECT sp.status,
				COUNT(DISTINCT sp.name) as project_count,
				COALESCE(SUM(j.planned_cost), 0) as total_planned_cost,
				COALESCE(SUM(j.actual_cost), 0) as total_actual_cost,
				COALESCE(SUM(j.planned_revenue), 0) as total_planned_revenue,
				COALESCE(SUM(j.actual_revenue), 0) as total_actual_revenue
			FROM `tabSpecial Project` sp
			LEFT JOIN `tabSpecial Project Job` j ON j.parent = sp.name AND j.parenttype = 'Special Project'
			WHERE {where}
			GROUP BY sp.status
			ORDER BY FIELD(sp.status, 'Draft', 'Scoping', 'Booked', 'Planning', 'Approved', 'In Progress', 'On Hold', 'Completed', 'Cancelled')
			""".format(where=where),
			values,
			as_dict=1,
		)
		for r in rows:
			r["total_margin"] = (r["total_actual_revenue"] or 0) - (r["total_actual_cost"] or 0)
			rev = r["total_actual_revenue"] or 0
			r["margin_pct"] = (r["total_margin"] / rev * 100) if rev else 0
		return rows

	# None - project level
	rows = frappe.db.sql(
		"""
		SELECT sp.name, sp.project_name, sp.customer, sp.status,
			COALESCE(SUM(j.planned_cost), 0) as total_planned_cost,
			COALESCE(SUM(j.actual_cost), 0) as total_actual_cost,
			COALESCE(SUM(j.planned_revenue), 0) as total_planned_revenue,
			COALESCE(SUM(j.actual_revenue), 0) as total_actual_revenue
		FROM `tabSpecial Project` sp
		LEFT JOIN `tabSpecial Project Job` j ON j.parent = sp.name AND j.parenttype = 'Special Project'
		WHERE {where}
		GROUP BY sp.name, sp.project_name, sp.customer, sp.status
		ORDER BY sp.modified DESC
		""".format(where=where),
		values,
		as_dict=1,
	)

	for r in rows:
		r["total_margin"] = (r["total_actual_revenue"] or 0) - (r["total_actual_cost"] or 0)
		rev = r["total_actual_revenue"] or 0
		r["margin_pct"] = (r["total_margin"] / rev * 100) if rev else 0

	return rows
