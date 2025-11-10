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
		FROM `tabSea Shipment`
		WHERE docstatus = 1 {conditions}
	""".format(conditions=conditions), filters, as_dict=1)[0].count
	
	# On-Time Performance (based on ETA vs actual arrival)
	on_time_data = frappe.db.sql("""
		SELECT
			COUNT(*) as total,
			SUM(CASE WHEN eta IS NOT NULL AND actual_arrival IS NOT NULL 
				AND TIMESTAMPDIFF(DAY, eta, actual_arrival) <= 0 THEN 1 ELSE 0 END) as on_time
		FROM `tabSea Shipment`
		WHERE docstatus = 1 {conditions}
		AND eta IS NOT NULL AND actual_arrival IS NOT NULL
	""".format(conditions=conditions), filters, as_dict=1)[0]
	
	on_time_percentage = (on_time_data.on_time / on_time_data.total * 100) if on_time_data.total > 0 else 0
	
	# Revenue
	revenue_data = frappe.db.sql("""
		SELECT
			COALESCE(SUM(sfc.total_amount), 0) as total_revenue
		FROM `tabSea Shipment` sship
		LEFT JOIN `tabSea Freight Charges` sfc ON sfc.parent = sship.name
		WHERE sship.docstatus = 1 {conditions}
		GROUP BY sship.name
	""".format(conditions=conditions), filters, as_dict=1)
	
	total_revenue = sum(flt(row.total_revenue) for row in revenue_data)
	
	# Total Weight and Volume
	weight_volume_data = frappe.db.sql("""
		SELECT
			COALESCE(SUM(total_weight), 0) as total_weight,
			COALESCE(SUM(total_volume), 0) as total_volume,
			COALESCE(SUM(total_containers), 0) as total_containers
		FROM `tabSea Shipment`
		WHERE docstatus = 1 {conditions}
	""".format(conditions=conditions), filters, as_dict=1)[0]
	
	# Delayed Shipments
	delayed_data = frappe.db.sql("""
		SELECT COUNT(*) as count
		FROM `tabSea Shipment`
		WHERE docstatus = 1 {conditions}
		AND has_delays = 1
	""".format(conditions=conditions), filters, as_dict=1)[0].count
	
	# Penalties
	penalty_data = frappe.db.sql("""
		SELECT
			COUNT(*) as shipments_with_penalties,
			COALESCE(SUM(estimated_penalty_amount), 0) as total_penalties
		FROM `tabSea Shipment`
		WHERE docstatus = 1 {conditions}
		AND has_penalties = 1
	""".format(conditions=conditions), filters, as_dict=1)[0]
	
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
		"metric": "Total Weight (kg)",
		"value": f"{flt(weight_volume_data.total_weight):,.2f}",
		"trend": "",
		"indicator": "blue"
	})
	
	metrics.append({
		"metric": "Total Volume (m³)",
		"value": f"{flt(weight_volume_data.total_volume):,.2f}",
		"trend": "",
		"indicator": "blue"
	})
	
	metrics.append({
		"metric": "Total Containers",
		"value": str(int(weight_volume_data.total_containers)),
		"trend": "",
		"indicator": "blue"
	})
	
	metrics.append({
		"metric": "Delayed Shipments",
		"value": str(delayed_data),
		"trend": "",
		"indicator": "red" if delayed_data > 0 else "green"
	})
	
	metrics.append({
		"metric": "Shipments with Penalties",
		"value": str(penalty_data.shipments_with_penalties),
		"trend": "",
		"indicator": "red" if penalty_data.shipments_with_penalties > 0 else "green"
	})
	
	metrics.append({
		"metric": "Total Penalties",
		"value": f"{flt(penalty_data.total_penalties):,.2f}",
		"trend": "",
		"indicator": "red" if penalty_data.total_penalties > 0 else "green"
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
	
	if filters.get("shipping_line"):
		conditions.append("shipping_line = %(shipping_line)s")
	
	if filters.get("status"):
		conditions.append("shipping_status = %(status)s")
	
	return " AND " + " AND ".join(conditions) if conditions else ""

def get_chart_data(data):
	if not data:
		return None
	
	# Performance metrics chart - show key metrics
	# Extract numeric values from metrics
	metrics_to_chart = []
	values_to_chart = []
	
	for row in data:
		metric = row.get("metric", "")
		value_str = str(row.get("value", "0")).replace(",", "").replace("%", "")
		try:
			# Try to extract numeric value
			if "Total" in metric or "Revenue" in metric or "Penalties" in metric:
				value = float(value_str)
				metrics_to_chart.append(metric)
				values_to_chart.append(value)
		except:
			pass
	
	if not metrics_to_chart:
		return None
	
	chart = {
		"data": {
			"labels": metrics_to_chart[:5],  # Limit to 5 metrics
			"datasets": [{
				"name": "Value",
				"values": values_to_chart[:5]
			}]
		},
		"type": "bar",
		"colors": ["#5e64ff"]
	}
	
	return chart

def get_summary(data, filters):
	return []

