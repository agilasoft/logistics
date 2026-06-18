# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"fieldname": "exhibit", "label": _("MICE Project"), "fieldtype": "Link", "options": "MICE Project", "width": 160},
		{"fieldname": "organizer", "label": _("Organizer"), "fieldtype": "Link", "options": "MICE Organizer", "width": 160},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 140},
		{"fieldname": "billing_status", "label": _("Billing Status"), "fieldtype": "Data", "width": 120},
		{"fieldname": "lifecycle_stage", "label": _("Lifecycle Stage"), "fieldtype": "Data", "width": 100},
		{"fieldname": "billing_lines", "label": _("Billing Lines"), "fieldtype": "Int", "width": 90},
		{"fieldname": "invoiced_lines", "label": _("Invoiced"), "fieldtype": "Int", "width": 80},
	]
	conditions = ["ep.docstatus < 2"]
	values = {}
	if filters.get("organizer"):
		conditions.append("ep.organizer = %(organizer)s")
		values["organizer"] = filters["organizer"]
	if filters.get("customer"):
		conditions.append("org.customer = %(customer)s")
		values["customer"] = filters["customer"]
	if filters.get("billing_status"):
		conditions.append("ep.billing_status = %(billing_status)s")
		values["billing_status"] = filters["billing_status"]
	where = " AND ".join(conditions)
	rows = frappe.db.sql(
		f"""
		SELECT ep.name AS exhibit,
			ep.organizer,
			org.customer AS customer,
			ep.billing_status,
			ep.lifecycle_stage,
			(SELECT COUNT(*) FROM `tabMICE Project Billing` b WHERE b.parent = ep.name) AS billing_lines,
			(SELECT COUNT(*) FROM `tabMICE Project Billing` b WHERE b.parent = ep.name AND b.status = 'Invoiced') AS invoiced_lines
		FROM `tabMICE Project` ep
			LEFT JOIN `tabMICE Organizer` org ON org.name = ep.organizer
		WHERE {where}
		ORDER BY ep.modified DESC
		""",
		values,
		as_dict=1,
	)
	return columns, rows
