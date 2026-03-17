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
		{"fieldname": "name", "label": _("Request"), "fieldtype": "Link", "options": "Special Project Request", "width": 150},
		{"fieldname": "special_project", "label": _("Special Project"), "fieldtype": "Link", "options": "Special Project", "width": 130},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 130},
		{"fieldname": "priority", "label": _("Priority"), "fieldtype": "Data", "width": 90},
		{"fieldname": "request_date", "label": _("Request Date"), "fieldtype": "Date", "width": 110},
		{"fieldname": "required_by", "label": _("Required By"), "fieldtype": "Date", "width": 110},
		{"fieldname": "requested_by", "label": _("Requested By"), "fieldtype": "Link", "options": "User", "width": 120},
		{"fieldname": "resource_count", "label": _("Resource Reqs"), "fieldtype": "Int", "width": 90},
		{"fieldname": "product_count", "label": _("Product Reqs"), "fieldtype": "Int", "width": 90},
		{"fieldname": "equipment_count", "label": _("Equipment Reqs"), "fieldtype": "Int", "width": 100},
		{"fieldname": "creation", "label": _("Created"), "fieldtype": "Datetime", "width": 130},
	]


def get_data(filters):
	conditions = []
	values = {}

	if filters.get("status"):
		conditions.append("spr.status = %(status)s")
		values["status"] = filters["status"]
	if filters.get("special_project"):
		conditions.append("spr.special_project = %(special_project)s")
		values["special_project"] = filters["special_project"]
	if filters.get("priority"):
		conditions.append("spr.priority = %(priority)s")
		values["priority"] = filters["priority"]
	if filters.get("required_by_from"):
		conditions.append("spr.required_by >= %(required_by_from)s")
		values["required_by_from"] = filters["required_by_from"]
	if filters.get("required_by_to"):
		conditions.append("spr.required_by <= %(required_by_to)s")
		values["required_by_to"] = filters["required_by_to"]

	where = " AND ".join(conditions) if conditions else "1=1"

	rows = frappe.db.sql(
		"""
		SELECT spr.name, spr.special_project, spr.status, spr.priority,
			spr.request_date, spr.required_by, spr.requested_by, spr.creation
		FROM `tabSpecial Project Request` spr
		WHERE {where}
		ORDER BY spr.modified DESC
		""".format(where=where),
		values,
		as_dict=1,
	)

	# Add counts for resource/product/equipment requests
	for row in rows:
		row["resource_count"] = frappe.db.count(
			"Special Project Resource Request",
			filters={"parent": row["name"], "parenttype": "Special Project Request"},
		)
		row["product_count"] = frappe.db.count(
			"Special Project Product Request",
			filters={"parent": row["name"], "parenttype": "Special Project Request"},
		)
		row["equipment_count"] = frappe.db.count(
			"Special Project Equipment Request",
			filters={"parent": row["name"], "parenttype": "Special Project Request"},
		)

	return rows
