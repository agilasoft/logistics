# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, flt


def execute(filters=None):
	f = frappe._dict(filters or {})
	
	columns = get_columns()
	data = get_data(f)
	
	return columns, data


def get_columns():
	return [
		{"label": "Period", "fieldname": "period", "fieldtype": "Data", "width": 120},
		{"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 150},
		{"label": "Declaration Type", "fieldname": "declaration_type", "fieldtype": "Data", "width": 120},
		{"label": "Count", "fieldname": "count", "fieldtype": "Int", "width": 80},
		{"label": "Total Value", "fieldname": "total_value", "fieldtype": "Currency", "width": 120},
		{"label": "Currency", "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 80},
		{"label": "Avg Value", "fieldname": "avg_value", "fieldtype": "Currency", "width": 120},
		{"label": "Min Value", "fieldname": "min_value", "fieldtype": "Currency", "width": 120},
		{"label": "Max Value", "fieldname": "max_value", "fieldtype": "Currency", "width": 120}
	]


def get_data(filters):
	conditions = get_conditions(filters)
	group_by = get_group_by(filters)
	
	group_by_fields = get_group_by_fields(filters)
	group_by_clause = group_by + ", d.currency" if group_by != "1" else "d.currency"
	
	data = frappe.db.sql("""
		SELECT
			{group_by_fields}
			COUNT(d.name) as count,
			SUM(COALESCE(d.declaration_value, 0)) as total_value,
			d.currency,
			AVG(COALESCE(d.declaration_value, 0)) as avg_value,
			MIN(COALESCE(d.declaration_value, 0)) as min_value,
			MAX(COALESCE(d.declaration_value, 0)) as max_value
		FROM `tabDeclaration` d
		WHERE d.docstatus != 2
		{conditions}
		GROUP BY {group_by_clause}
		ORDER BY total_value DESC
	""".format(
		group_by_fields=group_by_fields,
		conditions=conditions,
		group_by_clause=group_by_clause
	), filters, as_dict=1)
	
	# Format the period field
	for row in data:
		if filters.get("group_by") == "Month":
			row.period = getattr(row, 'period_month', "")
		elif filters.get("group_by") == "Week":
			row.period = getattr(row, 'period_week', "")
		elif filters.get("group_by") == "Day":
			row.period = getattr(row, 'period_day', "")
		elif filters.get("group_by") == "Customer":
			row.period = getattr(row, 'customer', "")
		elif filters.get("group_by") == "Declaration Type":
			row.period = getattr(row, 'declaration_type', "")
		else:
			row.period = "All"
	
	return data


def get_group_by_fields(filters):
	group_by = filters.get("group_by", "None")
	
	if group_by == "Month":
		return "DATE_FORMAT(d.declaration_date, '%%Y-%%m') as period_month, "
	elif group_by == "Week":
		return "DATE_FORMAT(d.declaration_date, '%%Y-%%u') as period_week, "
	elif group_by == "Day":
		return "DATE_FORMAT(d.declaration_date, '%%Y-%%m-%%d') as period_day, "
	elif group_by == "Customer":
		return "d.customer, "
	elif group_by == "Declaration Type":
		return "d.declaration_type, "
	else:
		return ""


def get_group_by(filters):
	group_by = filters.get("group_by", "None")
	
	if group_by == "Month":
		return "DATE_FORMAT(d.declaration_date, '%Y-%m')"
	elif group_by == "Week":
		return "DATE_FORMAT(d.declaration_date, '%Y-%u')"
	elif group_by == "Day":
		return "DATE_FORMAT(d.declaration_date, '%Y-%m-%d')"
	elif group_by == "Customer":
		return "d.customer"
	elif group_by == "Declaration Type":
		return "d.declaration_type"
	else:
		return "1"


def get_conditions(filters):
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("d.declaration_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("d.declaration_date <= %(to_date)s")
	
	if filters.get("customer"):
		conditions.append("d.customer = %(customer)s")
	
	if filters.get("declaration_type"):
		conditions.append("d.declaration_type = %(declaration_type)s")
	
	if filters.get("status"):
		conditions.append("d.status = %(status)s")
	
	if filters.get("company"):
		conditions.append("d.company = %(company)s")
	
	if filters.get("customs_authority"):
		conditions.append("d.customs_authority = %(customs_authority)s")
	
	return " AND " + " AND ".join(conditions) if conditions else ""

