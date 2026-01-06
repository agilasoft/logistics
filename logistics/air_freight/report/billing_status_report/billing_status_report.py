# Copyright (c) 2025, logistics.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate
from datetime import datetime, timedelta

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)
	summary = get_summary(data, filters)
	
	return columns, data, None, chart, summary

def get_columns():
	return [
		{
			"fieldname": "air_shipment",
			"label": _("Air Shipment"),
			"fieldtype": "Link",
			"options": "Air Shipment",
			"width": 150
		},
		{
			"fieldname": "booking_date",
			"label": _("Booking Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150
		},
		{
			"fieldname": "sales_quote",
			"label": _("Sales Quote"),
			"fieldtype": "Link",
			"options": "Sales Quote",
			"width": 150
		},
		{
			"fieldname": "billing_status",
			"label": _("Billing Status"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "total_charges",
			"label": _("Total Charges"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "billing_amount",
			"label": _("Billing Amount"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "billing_date",
			"label": _("Billing Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "sales_invoice",
			"label": _("Sales Invoice"),
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 150
		},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Data",
			"width": 80
		},
		{
			"fieldname": "days_since_booking",
			"label": _("Days Since Booking"),
			"fieldtype": "Int",
			"width": 130
		},
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 120
		}
	]

def get_data(filters):
	conditions = get_conditions(filters)
	
	data = frappe.db.sql("""
		SELECT
			aship.name as air_shipment,
			aship.booking_date,
			aship.local_customer as customer,
			aship.sales_quote,
			aship.billing_status,
			COALESCE(SUM(asc.total_amount), 0) as total_charges,
			COALESCE(aship.billing_amount, 0) as billing_amount,
			aship.billing_date,
			aship.sales_invoice,
			COALESCE(MAX(asc.currency), aship.billing_currency, 'USD') as currency,
			DATEDIFF(CURDATE(), aship.booking_date) as days_since_booking,
			aship.company
		FROM
			`tabAir Shipment` aship
		LEFT JOIN
			`tabAir Shipment Charges` asc ON asc.parent = aship.name
		WHERE
			aship.docstatus = 1
			{conditions}
		GROUP BY
			aship.name
		ORDER BY
			aship.booking_date DESC, aship.name DESC
	""".format(conditions=conditions), filters, as_dict=1)
	
	return data

def get_conditions(filters):
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("aship.booking_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("aship.booking_date <= %(to_date)s")
	
	if filters.get("company"):
		conditions.append("aship.company = %(company)s")
	
	if filters.get("customer"):
		conditions.append("aship.local_customer = %(customer)s")
	
	if filters.get("billing_status"):
		conditions.append("aship.billing_status = %(billing_status)s")
	
	if filters.get("unbilled_only"):
		conditions.append("aship.billing_status IN ('Not Billed', 'Pending')")
	
	if filters.get("overdue_days"):
		conditions.append("DATEDIFF(CURDATE(), aship.booking_date) > %(overdue_days)s")
		conditions.append("aship.billing_status IN ('Not Billed', 'Pending')")
	
	return " AND " + " AND ".join(conditions) if conditions else ""

def get_chart_data(data):
	if not data:
		return None
	
	# Billing status distribution
	billing_count = {
		"Not Billed": 0,
		"Pending": 0,
		"Billed": 0,
		"Partially Billed": 0,
		"Overdue": 0,
		"Cancelled": 0
	}
	
	for row in data:
		status = row.get("billing_status") or "Not Billed"
		billing_count[status] = billing_count.get(status, 0) + 1
	
	chart = {
		"data": {
			"labels": list(billing_count.keys()),
			"datasets": [{
				"name": "Billing Status",
				"values": list(billing_count.values())
			}]
		},
		"type": "pie",
		"colors": ["#7cd6fd", "#ffa00a", "#28a745", "#5e64ff", "#ff5858", "#743ee2"]
	}
	
	return chart

def get_summary(data, filters):
	if not data:
		return []
	
	total_shipments = len(data)
	total_charges = sum(flt(row.get("total_charges") or 0) for row in data)
	total_billed = sum(flt(row.get("billing_amount") or 0) for row in data if row.get("billing_status") in ["Billed", "Partially Billed"])
	unbilled_amount = total_charges - total_billed
	
	billed_count = sum(1 for row in data if row.get("billing_status") in ["Billed", "Partially Billed"])
	unbilled_count = total_shipments - billed_count
	
	overdue_count = sum(1 for row in data if row.get("days_since_booking", 0) > 30 and row.get("billing_status") in ["Not Billed", "Pending"])
	
	summary = [
		{
			"label": _("Total Shipments"),
			"value": total_shipments,
			"indicator": "blue"
		},
		{
			"label": _("Total Charges"),
			"value": f"{total_charges:,.2f}",
			"indicator": "blue"
		},
		{
			"label": _("Billed Amount"),
			"value": f"{total_billed:,.2f}",
			"indicator": "green"
		},
		{
			"label": _("Unbilled Amount"),
			"value": f"{unbilled_amount:,.2f}",
			"indicator": "orange"
		},
		{
			"label": _("Billed Shipments"),
			"value": billed_count,
			"indicator": "green"
		},
		{
			"label": _("Unbilled Shipments"),
			"value": unbilled_count,
			"indicator": "orange"
		},
		{
			"label": _("Overdue (>30 days)"),
			"value": overdue_count,
			"indicator": "red"
		}
	]
	
	return summary


