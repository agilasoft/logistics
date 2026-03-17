# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "name", "label": _("Project"), "fieldtype": "Link", "options": "Special Project", "width": 130},
		{"fieldname": "project_name", "label": _("Project Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 150},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 110},
		{"fieldname": "planned_cost", "label": _("Planned Cost"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "actual_cost", "label": _("Actual Cost"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "planned_revenue", "label": _("Planned Revenue"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "actual_revenue", "label": _("Actual Revenue"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "planned_margin", "label": _("Planned Margin"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "actual_margin", "label": _("Actual Margin"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "cost_variance", "label": _("Cost Variance"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "revenue_variance", "label": _("Revenue Variance"), "fieldtype": "Currency", "width": 120},
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
	if filters.get("status"):
		conditions.append("sp.status = %(status)s")
		values["status"] = filters["status"]

	where = " AND ".join(conditions)

	rows = frappe.db.sql(
		"""
		SELECT sp.name, sp.project_name, sp.customer, sp.status,
			COALESCE(SUM(j.planned_cost), 0) as planned_cost,
			COALESCE(SUM(j.actual_cost), 0) as actual_cost,
			COALESCE(SUM(j.planned_revenue), 0) as planned_revenue,
			COALESCE(SUM(j.actual_revenue), 0) as actual_revenue
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
		r["planned_margin"] = (r["planned_revenue"] or 0) - (r["planned_cost"] or 0)
		r["actual_margin"] = (r["actual_revenue"] or 0) - (r["actual_cost"] or 0)
		r["cost_variance"] = (r["actual_cost"] or 0) - (r["planned_cost"] or 0)
		r["revenue_variance"] = (r["actual_revenue"] or 0) - (r["planned_revenue"] or 0)

	return rows
