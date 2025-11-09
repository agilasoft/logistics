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
			"fieldname": "metric",
			"label": _("Metric"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "value",
			"label": _("Value"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "trend",
			"label": _("Trend"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "indicator",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100
		}
	]

def get_data(filters):
	conditions = get_conditions(filters)
	
	# Get performance metrics
	metrics = []
	
	# Total Shipments
	total_shipments = frappe.db.sql("""
		SELECT COUNT(*) as count
		FROM `tabAir Shipment`
		WHERE docstatus = 1 {conditions}
	""".format(conditions=conditions), filters, as_dict=1)[0].count
	
	# On-Time Performance
	on_time_data = frappe.db.sql("""
		SELECT
			COUNT(*) as total,
			SUM(CASE WHEN eta IS NOT NULL AND actual_arrival IS NOT NULL 
				AND TIMESTAMPDIFF(HOUR, eta, actual_arrival) <= 0 THEN 1 ELSE 0 END) as on_time
		FROM `tabAir Shipment`
		WHERE docstatus = 1 {conditions}
		AND eta IS NOT NULL AND actual_arrival IS NOT NULL
	""".format(conditions=conditions), filters, as_dict=1)[0]
	
	on_time_percentage = (on_time_data.on_time / on_time_data.total * 100) if on_time_data.total > 0 else 0
	
	# Revenue
	revenue_data = frappe.db.sql("""
		SELECT
			COALESCE(SUM(asc.total_amount), 0) as total_revenue
		FROM `tabAir Shipment` aship
		LEFT JOIN `tabAir Shipment Charges` asc ON asc.parent = aship.name
		WHERE aship.docstatus = 1 {conditions}
		GROUP BY aship.name
	""".format(conditions=conditions), filters, as_dict=1)
	
	total_revenue = sum(flt(row.total_revenue) for row in revenue_data)
	
	# Billing Status
	billing_data = frappe.db.sql("""
		SELECT
			billing_status,
			COUNT(*) as count
		FROM `tabAir Shipment`
		WHERE docstatus = 1 {conditions}
		GROUP BY billing_status
	""".format(conditions=conditions), filters, as_dict=1)
	
	billed_count = sum(row.count for row in billing_data if row.billing_status in ["Billed", "Partially Billed"])
	unbilled_count = sum(row.count for row in billing_data if row.billing_status in ["Not Billed", "Pending"])
	
	# Build metrics
	metrics.append({
		"metric": "Total Shipments",
		"value": str(total_shipments),
		"trend": "",
		"indicator": "blue"
	})
	
	metrics.append({
		"metric": "On-Time Performance",
		"value": f"{on_time_percentage:.1f}%",
		"trend": "",
		"indicator": "green" if on_time_percentage >= 90 else "orange" if on_time_percentage >= 75 else "red"
	})
	
	metrics.append({
		"metric": "Total Revenue",
		"value": f"{total_revenue:,.2f}",
		"trend": "",
		"indicator": "green"
	})
	
	metrics.append({
		"metric": "Billed Shipments",
		"value": str(billed_count),
		"trend": "",
		"indicator": "green"
	})
	
	metrics.append({
		"metric": "Unbilled Shipments",
		"value": str(unbilled_count),
		"trend": "",
		"indicator": "orange"
	})
	
	return metrics

def get_conditions(filters):
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("booking_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("booking_date <= %(to_date)s")
	
	if filters.get("company"):
		conditions.append("company = %(company)s")
	
	return " AND " + " AND ".join(conditions) if conditions else ""

def get_chart_data(data):
	# Performance metrics chart
	chart = {
		"data": {
			"labels": [row.get("metric") for row in data],
			"datasets": [{
				"name": "Performance Metrics",
				"values": [1] * len(data)  # Placeholder values
			}]
		},
		"type": "bar",
		"colors": ["#5e64ff"]
	}
	
	return chart

def get_summary(data, filters):
	return []


