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
			"fieldname": "sea_shipment",
			"label": _("Sea Shipment"),
			"fieldtype": "Link",
			"options": "Sea Shipment",
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
			"fieldname": "origin_port",
			"label": _("Origin"),
			"fieldtype": "Link",
			"options": "UNLOCO",
			"width": 120
		},
		{
			"fieldname": "destination_port",
			"label": _("Destination"),
			"fieldtype": "Link",
			"options": "UNLOCO",
			"width": 120
		},
		{
			"fieldname": "chargeable",
			"label": _("Chargeable (kg)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 120
		},
		{
			"fieldname": "total_containers",
			"label": _("Containers"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "total_charges",
			"label": _("Total Charges"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "revenue_amount",
			"label": _("Revenue Amount"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "billing_status",
			"label": _("Billing Status"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Data",
			"width": 80
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
	
	# Get Sea Shipments with charges
	data = frappe.db.sql("""
		SELECT
			sship.name as sea_shipment,
			sship.booking_date,
			sship.local_customer as customer,
			sship.origin_port,
			sship.destination_port,
			sship.chargeable,
			sship.total_containers,
			COALESCE(SUM(sfc.total_amount), 0) as total_charges,
			COALESCE(sship.revenue_amount, 0) as revenue_amount,
			sship.billing_status,
			COALESCE(MAX(sfc.currency), sship.currency, 'USD') as currency,
			sship.company
		FROM
			`tabSea Shipment` sship
		LEFT JOIN
			`tabSea Freight Charges` sfc ON sfc.parent = sship.name
		WHERE
			sship.docstatus = 1
			{conditions}
		GROUP BY
			sship.name
		ORDER BY
			sship.booking_date DESC, sship.name DESC
	""".format(conditions=conditions), filters, as_dict=1)
	
	return data

def get_conditions(filters):
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("sship.booking_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("sship.booking_date <= %(to_date)s")
	
	if filters.get("company"):
		conditions.append("sship.company = %(company)s")
	
	if filters.get("customer"):
		conditions.append("sship.local_customer = %(customer)s")
	
	if filters.get("billing_status"):
		conditions.append("sship.billing_status = %(billing_status)s")
	
	return " AND " + " AND ".join(conditions) if conditions else ""

def get_chart_data(data):
	if not data:
		return None
	
	# Revenue by month chart
	monthly_revenue = {}
	for row in data:
		if row.get("booking_date"):
			month_key = row["booking_date"].strftime("%Y-%m")
			revenue = flt(row.get("total_charges") or row.get("revenue_amount") or 0)
			monthly_revenue[month_key] = monthly_revenue.get(month_key, 0) + revenue
	
	chart = {
		"data": {
			"labels": sorted(monthly_revenue.keys()),
			"datasets": [{
				"name": "Revenue",
				"values": [monthly_revenue[k] for k in sorted(monthly_revenue.keys())]
			}]
		},
		"type": "line",
		"colors": ["#5e64ff"]
	}
	
	return chart

def get_summary(data, filters):
	if not data:
		return []
	
	total_shipments = len(data)
	total_revenue = sum(flt(row.get("total_charges") or row.get("revenue_amount") or 0) for row in data)
	total_chargeable = sum(flt(row.get("chargeable") or 0) for row in data)
	total_containers = sum(flt(row.get("total_containers") or 0) for row in data)
	avg_revenue_per_kg = total_revenue / total_chargeable if total_chargeable > 0 else 0
	
	# Count by billing status
	billed_count = sum(1 for row in data if row.get("billing_status") in ["Billed", "Partially Billed"])
	unbilled_count = total_shipments - billed_count
	
	summary = [
		{
			"label": _("Total Shipments"),
			"value": total_shipments,
			"indicator": "blue"
		},
		{
			"label": _("Total Revenue"),
			"value": f"{total_revenue:,.2f}",
			"indicator": "green"
		},
		{
			"label": _("Total Containers"),
			"value": int(total_containers),
			"indicator": "blue"
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
			"label": _("Avg Revenue per kg"),
			"value": f"{avg_revenue_per_kg:,.2f}",
			"indicator": "blue"
		}
	]
	
	return summary

