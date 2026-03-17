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
		{"fieldname": "special_project", "label": _("Special Project"), "fieldtype": "Link", "options": "Special Project", "width": 130},
		{"fieldname": "project_name", "label": _("Project Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "delivery_date", "label": _("Delivery Date"), "fieldtype": "Date", "width": 110},
		{"fieldname": "delivery_type", "label": _("Type"), "fieldtype": "Data", "width": 110},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
		{"fieldname": "description", "label": _("Description"), "fieldtype": "Data", "width": 200},
	]


def get_data(filters):
	conditions = ["d.parent = sp.name"]
	values = {}

	if filters.get("status"):
		conditions.append("d.status = %(status)s")
		values["status"] = filters["status"]
	if filters.get("delivery_type"):
		conditions.append("d.delivery_type = %(delivery_type)s")
		values["delivery_type"] = filters["delivery_type"]
	if filters.get("special_project"):
		conditions.append("sp.name = %(special_project)s")
		values["special_project"] = filters["special_project"]
	if filters.get("from_date"):
		conditions.append("d.delivery_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("d.delivery_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]

	where = " AND ".join(conditions)

	return frappe.db.sql(
		"""
		SELECT sp.name as special_project, sp.project_name, d.delivery_date, d.delivery_type, d.status, d.description
		FROM `tabSpecial Project` sp
		INNER JOIN `tabSpecial Project Delivery` d ON d.parent = sp.name AND d.parenttype = 'Special Project'
		WHERE {where}
		ORDER BY d.delivery_date ASC, sp.name
		""".format(where=where),
		values,
		as_dict=1,
	)
