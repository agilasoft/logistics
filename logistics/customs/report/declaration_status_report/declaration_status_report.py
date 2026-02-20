# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, flt


def execute(filters=None):
	f = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(f)
	chart = get_chart_data(data) if data else None
	summary = get_summary(data) if data else []
	return columns, data, None, chart, summary


def get_columns():
	return [
		{"label": "Declaration", "fieldname": "declaration", "fieldtype": "Link", "options": "Declaration", "width": 150},
		{"label": "Date", "fieldname": "declaration_date", "fieldtype": "Date", "width": 100},
		{"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 150},
		{"label": "Customs Authority", "fieldname": "customs_authority", "fieldtype": "Link", "options": "Customs Authority", "width": 150},
		{"label": "Type", "fieldname": "declaration_type", "fieldtype": "Data", "width": 100},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
		{"label": "Value", "fieldname": "declaration_value", "fieldtype": "Currency", "width": 120},
		{"label": "Currency", "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 80},
		{"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 120}
	]


def get_data(filters):
	conditions = get_conditions(filters)
	
	data = frappe.db.sql("""
		SELECT
			d.name as declaration,
			d.declaration_date,
			d.customer,
			d.customs_authority,
			d.declaration_type,
			d.status,
			d.declaration_value,
			d.currency,
			d.company
		FROM `tabDeclaration` d
		WHERE d.docstatus != 2
		{conditions}
		ORDER BY d.declaration_date DESC, d.name DESC
	""".format(conditions=conditions), filters, as_dict=1)
	
	return data


def get_conditions(filters):
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("d.declaration_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("d.declaration_date <= %(to_date)s")
	
	if filters.get("customer"):
		conditions.append("d.customer = %(customer)s")
	
	if filters.get("customs_authority"):
		conditions.append("d.customs_authority = %(customs_authority)s")
	
	if filters.get("declaration_type"):
		conditions.append("d.declaration_type = %(declaration_type)s")
	
	if filters.get("status"):
		conditions.append("d.status = %(status)s")
	
	if filters.get("company"):
		conditions.append("d.company = %(company)s")
	
	return " AND " + " AND ".join(conditions) if conditions else ""


def get_chart_data(data):
	if not data:
		return None
	from collections import Counter
	by_status = Counter((r.get("status") or _("Unknown")) for r in data)
	return {
		"data": {
			"labels": list(by_status.keys()),
			"datasets": [{"name": _("Declarations"), "values": list(by_status.values())}]
		},
		"type": "bar",
		"colors": ["#5e64ff"]
	}
def get_summary(data):
	if not data:
		return []
	total = len(data)
	total_value = sum(flt(r.get("declaration_value")) for r in data)
	return [
		{"label": _("Total Declarations"), "value": total, "indicator": "blue"},
		{"label": _("Total Value"), "value": f"{total_value:,.2f}", "indicator": "green"},
	]