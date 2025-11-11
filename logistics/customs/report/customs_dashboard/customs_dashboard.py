# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, today, add_days, flt


def execute(filters=None):
	f = frappe._dict(filters or {})
	
	columns = get_columns()
	data = get_data(f)
	chart = get_chart_data(data, f)
	
	return columns, data, None, chart


def get_columns():
	return [
		{"label": "Metric", "fieldname": "metric", "fieldtype": "Data", "width": 200},
		{"label": "Value", "fieldname": "value", "fieldtype": "Data", "width": 150},
		{"label": "Details", "fieldname": "details", "fieldtype": "Data", "width": 300}
	]


def get_data(filters):
	data = []
	conditions = get_conditions(filters)
	
	# Total Declarations
	total = frappe.db.sql("""
		SELECT COUNT(*) as count
		FROM `tabDeclaration` d
		WHERE d.docstatus != 2
		{conditions}
	""".format(conditions=conditions), filters, as_dict=1)[0]
	
	data.append({
		"metric": "Total Declarations",
		"value": total.count,
		"details": "All declarations in the period"
	})
	
	# By Status
	status_breakdown = frappe.db.sql("""
		SELECT status, COUNT(*) as count
		FROM `tabDeclaration` d
		WHERE d.docstatus != 2
		{conditions}
		GROUP BY status
		ORDER BY count DESC
	""".format(conditions=conditions), filters, as_dict=1)
	
	status_details = ", ".join([f"{s.status}: {s.count}" for s in status_breakdown])
	data.append({
		"metric": "By Status",
		"value": "",
		"details": status_details
	})
	
	# Total Value
	total_value = frappe.db.sql("""
		SELECT 
			SUM(COALESCE(declaration_value, 0)) as total,
			currency
		FROM `tabDeclaration` d
		WHERE d.docstatus != 2
		{conditions}
		GROUP BY currency
	""".format(conditions=conditions), filters, as_dict=1)
	
	value_details = ", ".join([f"{flt(v.total, 2):,.2f} {v.currency}" for v in total_value])
	data.append({
		"metric": "Total Declaration Value",
		"value": "",
		"details": value_details
	})
	
	# Pending Approvals
	pending = frappe.db.sql("""
		SELECT COUNT(*) as count
		FROM `tabDeclaration` d
		WHERE d.docstatus != 2
		AND d.status IN ('Draft', 'Submitted', 'In Progress')
		{conditions}
	""".format(conditions=conditions), filters, as_dict=1)[0]
	
	data.append({
		"metric": "Pending Approvals",
		"value": pending.count,
		"details": "Declarations awaiting approval"
	})
	
	# Overdue Declarations
	overdue = frappe.db.sql("""
		SELECT COUNT(*) as count
		FROM `tabDeclaration` d
		WHERE d.docstatus != 2
		AND d.status NOT IN ('Approved', 'Rejected', 'Cancelled')
		AND DATEDIFF(CURDATE(), DATE_ADD(d.declaration_date, INTERVAL 5 DAY)) > 0
		{conditions}
	""".format(conditions=conditions), filters, as_dict=1)[0]
	
	data.append({
		"metric": "Overdue Declarations",
		"value": overdue.count,
		"details": "Past expected processing date"
	})
	
	# By Declaration Type
	type_breakdown = frappe.db.sql("""
		SELECT declaration_type, COUNT(*) as count
		FROM `tabDeclaration` d
		WHERE d.docstatus != 2
		AND declaration_type IS NOT NULL
		{conditions}
		GROUP BY declaration_type
		ORDER BY count DESC
	""".format(conditions=conditions), filters, as_dict=1)
	
	type_details = ", ".join([f"{t.declaration_type}: {t.count}" for t in type_breakdown])
	data.append({
		"metric": "By Type",
		"value": "",
		"details": type_details
	})
	
	# Top Customers
	top_customers = frappe.db.sql("""
		SELECT 
			customer,
			COUNT(*) as count,
			SUM(COALESCE(declaration_value, 0)) as total_value
		FROM `tabDeclaration` d
		WHERE d.docstatus != 2
		{conditions}
		GROUP BY customer
		ORDER BY count DESC
		LIMIT 5
	""".format(conditions=conditions), filters, as_dict=1)
	
	customer_details = ", ".join([f"{c.customer}: {c.count}" for c in top_customers])
	data.append({
		"metric": "Top 5 Customers",
		"value": "",
		"details": customer_details
	})
	
	# Average Processing Time (simplified)
	avg_days = frappe.db.sql("""
		SELECT AVG(DATEDIFF(CURDATE(), declaration_date)) as avg_days
		FROM `tabDeclaration` d
		WHERE d.docstatus != 2
		AND d.status IN ('Approved', 'Rejected')
		{conditions}
	""".format(conditions=conditions), filters, as_dict=1)[0]
	
	data.append({
		"metric": "Avg Processing Days",
		"value": f"{flt(avg_days.avg_days or 0, 1)} days" if avg_days.avg_days else "N/A",
		"details": "Average days to process completed declarations"
	})
	
	return data


def get_chart_data(data, filters):
	conditions = get_conditions(filters)
	
	# Status Chart
	status_data = frappe.db.sql("""
		SELECT status, COUNT(*) as count
		FROM `tabDeclaration` d
		WHERE d.docstatus != 2
		{conditions}
		GROUP BY status
		ORDER BY count DESC
	""".format(conditions=conditions), filters, as_dict=1)
	
	chart = {
		"data": {
			"labels": [s.status for s in status_data],
			"datasets": [{
				"name": "Declarations by Status",
				"values": [s.count for s in status_data]
			}]
		},
		"type": "pie",
		"colors": ["#5e64ff", "#28a745", "#ffc107", "#dc3545", "#17a2b8", "#6c757d"]
	}
	
	return chart


def get_conditions(filters):
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("d.declaration_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("d.declaration_date <= %(to_date)s")
	
	if filters.get("customer"):
		conditions.append("d.customer = %(customer)s")
	
	if filters.get("company"):
		conditions.append("d.company = %(company)s")
	
	if filters.get("customs_authority"):
		conditions.append("d.customs_authority = %(customs_authority)s")
	
	return " AND " + " AND ".join(conditions) if conditions else ""


