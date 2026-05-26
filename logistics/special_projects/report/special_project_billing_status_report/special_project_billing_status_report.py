# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from logistics.analytics_reports.bootstrap import tally_chart


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = tally_chart(data, "sales_invoice_status", _("SI status"))
	return columns, data, None, chart, []


def get_columns():
	return [
		{"fieldname": "special_project", "label": _("Special Project"), "fieldtype": "Link", "options": "Special Project", "width": 130},
		{"fieldname": "project_name", "label": _("Project Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 150},
		{"fieldname": "item_code", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 140},
		{"fieldname": "charge_type", "label": _("Charge Type"), "fieldtype": "Data", "width": 90},
		{"fieldname": "charge_category", "label": _("Charge Category"), "fieldtype": "Data", "width": 120},
		{"fieldname": "estimated_revenue", "label": _("Est. Revenue"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "sales_invoice_status", "label": _("SI Status"), "fieldtype": "Data", "width": 100},
	]


def get_data(filters):
	conditions = ["c.parent = sp.name", "c.parenttype = 'Special Project'", "c.parentfield = 'charges'"]
	values = {}

	if filters.get("sales_invoice_status"):
		conditions.append("IFNULL(c.sales_invoice_status,'') = %(sales_invoice_status)s")
		values["sales_invoice_status"] = filters["sales_invoice_status"]
	if filters.get("charge_type"):
		conditions.append("IFNULL(c.charge_type,'') = %(charge_type)s")
		values["charge_type"] = filters["charge_type"]
	if filters.get("special_project"):
		conditions.append("sp.name = %(special_project)s")
		values["special_project"] = filters["special_project"]
	if filters.get("customer"):
		conditions.append("sp.customer = %(customer)s")
		values["customer"] = filters["customer"]

	where = " AND ".join(conditions)

	return frappe.db.sql(
		"""
		SELECT sp.name as special_project, sp.project_name, sp.customer,
			c.item_code, c.charge_type, c.charge_category,
			c.estimated_revenue, IFNULL(c.sales_invoice_status,'') as sales_invoice_status
		FROM `tabSpecial Project` sp
		INNER JOIN `tabSpecial Project Charges` c ON c.parent = sp.name AND c.parenttype = 'Special Project' AND c.parentfield = 'charges'
		WHERE {where}
		ORDER BY sp.name, c.idx
		""".format(where=where),
		values,
		as_dict=1,
	)
