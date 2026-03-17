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
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 150},
		{"fieldname": "bill_type", "label": _("Bill Type"), "fieldtype": "Data", "width": 100},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 90},
		{"fieldname": "planned_amount", "label": _("Planned Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "sales_invoice", "label": _("Sales Invoice"), "fieldtype": "Link", "options": "Sales Invoice", "width": 120},
		{"fieldname": "invoice_date", "label": _("Invoice Date"), "fieldtype": "Date", "width": 100},
	]


def get_data(filters):
	conditions = ["b.parent = sp.name"]
	values = {}

	if filters.get("status"):
		conditions.append("b.status = %(status)s")
		values["status"] = filters["status"]
	if filters.get("bill_type"):
		conditions.append("b.bill_type = %(bill_type)s")
		values["bill_type"] = filters["bill_type"]
	if filters.get("special_project"):
		conditions.append("sp.name = %(special_project)s")
		values["special_project"] = filters["special_project"]
	if filters.get("customer"):
		conditions.append("sp.customer = %(customer)s")
		values["customer"] = filters["customer"]

	where = " AND ".join(conditions)

	return frappe.db.sql(
		"""
		SELECT sp.name as special_project, sp.project_name, sp.customer, b.bill_type, b.status,
			b.planned_amount, b.sales_invoice, b.invoice_date
		FROM `tabSpecial Project` sp
		INNER JOIN `tabSpecial Project Billing` b ON b.parent = sp.name AND b.parenttype = 'Special Project'
		WHERE {where}
		ORDER BY sp.name, b.sequence
		""".format(where=where),
		values,
		as_dict=1,
	)
