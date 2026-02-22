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
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 180},
		{"fieldname": "customer_name", "label": _("Customer Name"), "fieldtype": "Data", "width": 200},
		{"fieldname": "project_count", "label": _("Projects"), "fieldtype": "Int", "width": 90},
		{"fieldname": "active_count", "label": _("Active"), "fieldtype": "Int", "width": 80},
		{"fieldname": "completed_count", "label": _("Completed"), "fieldtype": "Int", "width": 90},
		{"fieldname": "total_planned_revenue", "label": _("Total Planned Revenue"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "total_actual_revenue", "label": _("Total Actual Revenue"), "fieldtype": "Currency", "width": 140},
	]


def get_data(filters):
	conditions = ["sp.customer IS NOT NULL AND sp.customer != ''"]
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

	return frappe.db.sql(
		"""
		SELECT sp.customer, c.customer_name,
			COUNT(DISTINCT sp.name) as project_count,
			SUM(CASE WHEN sp.status IN ('In Progress', 'Planning', 'Approved', 'Booked', 'Scoping') THEN 1 ELSE 0 END) as active_count,
			SUM(CASE WHEN sp.status = 'Completed' THEN 1 ELSE 0 END) as completed_count,
			COALESCE(SUM(j.planned_revenue), 0) as total_planned_revenue,
			COALESCE(SUM(j.actual_revenue), 0) as total_actual_revenue
		FROM `tabSpecial Project` sp
		LEFT JOIN `tabCustomer` c ON c.name = sp.customer
		LEFT JOIN `tabSpecial Project Job` j ON j.parent = sp.name AND j.parenttype = 'Special Project'
		WHERE {where}
		GROUP BY sp.customer, c.customer_name
		ORDER BY project_count DESC, total_actual_revenue DESC
		""".format(where=where),
		values,
		as_dict=1,
	)
