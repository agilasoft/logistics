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
		{"fieldname": "project_name", "label": _("Project Name"), "fieldtype": "Data", "width": 200},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 150},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 110},
		{"fieldname": "priority", "label": _("Priority"), "fieldtype": "Data", "width": 90},
		{"fieldname": "start_date", "label": _("Start Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "end_date", "label": _("End Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "planned_start", "label": _("Planned Start"), "fieldtype": "Date", "width": 110},
		{"fieldname": "planned_end", "label": _("Planned End"), "fieldtype": "Date", "width": 110},
		{"fieldname": "creation", "label": _("Created"), "fieldtype": "Datetime", "width": 130},
	]


def get_data(filters):
	conditions = []
	values = {}

	if filters.get("from_date"):
		conditions.append("DATE(sp.creation) >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("DATE(sp.creation) <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	if filters.get("status"):
		conditions.append("sp.status = %(status)s")
		values["status"] = filters["status"]
	if filters.get("customer"):
		conditions.append("sp.customer = %(customer)s")
		values["customer"] = filters["customer"]
	if filters.get("priority"):
		conditions.append("sp.priority = %(priority)s")
		values["priority"] = filters["priority"]

	where = " AND ".join(conditions) if conditions else "1=1"

	return frappe.db.sql(
		"""
		SELECT sp.name, sp.project_name, sp.customer, sp.status, sp.priority,
			sp.start_date, sp.end_date, sp.planned_start, sp.planned_end, sp.creation
		FROM `tabSpecial Project` sp
		WHERE {where}
		ORDER BY sp.modified DESC
		""".format(where=where),
		values,
		as_dict=1,
	)
