# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, get_datetime, format_datetime, format_date
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
			"fieldname": "transport_leg",
			"label": _("Transport Leg"),
			"fieldtype": "Link",
			"options": "Transport Leg",
			"width": 120
		},
		{
			"fieldname": "transport_job",
			"label": _("Transport Job"),
			"fieldtype": "Link",
			"options": "Transport Job",
			"width": 120
		},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "facility_from",
			"label": _("From Location"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "facility_to",
			"label": _("To Location"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "scheduled_delivery",
			"label": _("Scheduled Delivery"),
			"fieldtype": "Datetime",
			"width": 150
		},
		{
			"fieldname": "actual_delivery",
			"label": _("Actual Delivery"),
			"fieldtype": "Datetime",
			"width": 150
		},
		{
			"fieldname": "delivery_status",
			"label": _("Delivery Status"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "on_time_status",
			"label": _("On-Time Status"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "delay_minutes",
			"label": _("Delay (Minutes)"),
			"fieldtype": "Int",
			"width": 120
		},
		{
			"fieldname": "early_minutes",
			"label": _("Early (Minutes)"),
			"fieldtype": "Int",
			"width": 120
		},
		{
			"fieldname": "service_level",
			"label": _("Service Level"),
			"fieldtype": "Percent",
			"precision": 2,
			"width": 120
		},
		{
			"fieldname": "vehicle",
			"label": _("Vehicle"),
			"fieldtype": "Link",
			"options": "Transport Vehicle",
			"width": 120
		},
		{
			"fieldname": "driver",
			"label": _("Driver"),
			"fieldtype": "Link",
			"options": "Driver",
			"width": 120
		},
		{
			"fieldname": "transport_company",
			"label": _("Transport Company"),
			"fieldtype": "Link",
			"options": "Transport Company",
			"width": 150
		}
	]

def get_data(filters):
	conditions = get_conditions(filters)
	conditions_clause = (" AND " + conditions) if conditions else ""

	# Get delivery performance data
	query = """
		SELECT 
			tl.name as transport_leg,
			tl.transport_job,
			tj.customer,
			tl.facility_from,
			tl.facility_to,
			tl.drop_window_end as scheduled_delivery,
			tl.end_date as actual_delivery,
			tl.status as delivery_status,
			rs.vehicle,
			rs.driver,
			rs.transport_company,
			tl.drop_window_start,
			tl.drop_window_end,
			tl.start_date,
			tl.end_date
		FROM `tabTransport Leg` tl
		LEFT JOIN `tabTransport Job` tj ON tl.transport_job = tj.name
		LEFT JOIN `tabRun Sheet` rs ON tl.run_sheet = rs.name
		WHERE tl.docstatus = 1
		{conditions_clause}
		ORDER BY tl.end_date DESC
	""".format(conditions_clause=conditions_clause)
	
	data = frappe.db.sql(query, as_dict=True)
	
	# Process data and calculate metrics
	for row in data:
		row.customer = get_customer_name(row.transport_job)
		row.facility_from = get_facility_name(row.facility_from)
		row.facility_to = get_facility_name(row.facility_to)
		
		# Calculate on-time delivery metrics
		on_time_metrics = calculate_on_time_metrics(row)
		row.update(on_time_metrics)
		
		# Format dates
		if row.scheduled_delivery:
			row.scheduled_delivery = get_datetime(row.scheduled_delivery)
		if row.actual_delivery:
			row.actual_delivery = get_datetime(row.actual_delivery)
	
	return data

def get_conditions(filters):
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("tl.end_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("tl.end_date <= %(to_date)s")
	
	if filters.get("customer"):
		conditions.append("tj.customer = %(customer)s")
	
	if filters.get("vehicle"):
		conditions.append("rs.vehicle = %(vehicle)s")
	
	if filters.get("transport_company"):
		conditions.append("rs.transport_company = %(transport_company)s")
	
	if filters.get("delivery_status"):
		conditions.append("tl.status = %(delivery_status)s")
	
	if filters.get("on_time_status"):
		if filters.get("on_time_status") == "On Time":
			conditions.append("tl.end_date <= tl.drop_window_end")
		elif filters.get("on_time_status") == "Late":
			conditions.append("tl.end_date > tl.drop_window_end")
		elif filters.get("on_time_status") == "Early":
			conditions.append("tl.end_date < tl.drop_window_start")
	
	return " AND ".join(conditions) if conditions else ""

def get_customer_name(transport_job):
	"""Get customer name from transport job"""
	if not transport_job:
		return ""
	
	customer = frappe.db.get_value("Transport Job", transport_job, "customer")
	return customer or ""

def get_facility_name(facility):
	"""Get facility name"""
	if not facility:
		return ""
	
	# This would need to be implemented based on the actual facility structure
	return facility

def calculate_on_time_metrics(row):
	"""Calculate on-time delivery metrics"""
	metrics = {
		"on_time_status": "Unknown",
		"delay_minutes": 0,
		"early_minutes": 0,
		"service_level": 0
	}
	
	if not row.scheduled_delivery or not row.actual_delivery:
		return metrics
	
	scheduled = get_datetime(row.scheduled_delivery)
	actual = get_datetime(row.actual_delivery)
	window_start = get_datetime(row.drop_window_start) if row.drop_window_start else scheduled
	window_end = get_datetime(row.drop_window_end) if row.drop_window_end else scheduled
	
	# Calculate time differences
	if actual <= window_end:
		if actual >= window_start:
			metrics["on_time_status"] = "On Time"
			metrics["service_level"] = 100
		else:
			# Early delivery
			metrics["on_time_status"] = "Early"
			metrics["early_minutes"] = int((window_start - actual).total_seconds() / 60)
			metrics["service_level"] = 100  # Early is still good
	else:
		# Late delivery
		metrics["on_time_status"] = "Late"
		metrics["delay_minutes"] = int((actual - window_end).total_seconds() / 60)
		metrics["service_level"] = max(0, 100 - (metrics["delay_minutes"] / 60 * 10))  # Penalty for delay
	
	return metrics

def get_chart_data(data):
	"""Generate chart data for the report"""
	if not data:
		return None
	
	# On-time delivery performance chart
	on_time_count = len([row for row in data if row.on_time_status == "On Time"])
	early_count = len([row for row in data if row.on_time_status == "Early"])
	late_count = len([row for row in data if row.on_time_status == "Late"])
	
	chart = {
		"data": {
			"labels": ["On Time", "Early", "Late"],
			"datasets": [
				{
					"name": "Delivery Performance",
					"values": [on_time_count, early_count, late_count]
				}
			]
		},
		"type": "pie",
		"colors": ["#28a745", "#ffc107", "#dc3545"]
	}
	
	return chart

def get_summary(data, filters):
	"""Generate summary statistics"""
	if not data:
		return []
	
	total_deliveries = len(data)
	on_time_deliveries = len([row for row in data if row.on_time_status == "On Time"])
	late_deliveries = len([row for row in data if row.on_time_status == "Late"])
	early_deliveries = len([row for row in data if row.on_time_status == "Early"])
	
	on_time_percentage = (on_time_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0
	late_percentage = (late_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0
	
	avg_delay = sum(row.delay_minutes for row in data if row.delay_minutes > 0) / late_deliveries if late_deliveries > 0 else 0
	avg_early = sum(row.early_minutes for row in data if row.early_minutes > 0) / early_deliveries if early_deliveries > 0 else 0
	
	return [
		{
			"label": _("Total Deliveries"),
			"value": total_deliveries,
			"indicator": "blue"
		},
		{
			"label": _("On-Time Deliveries"),
			"value": on_time_deliveries,
			"indicator": "green"
		},
		{
			"label": _("Late Deliveries"),
			"value": late_deliveries,
			"indicator": "red"
		},
		{
			"label": _("Early Deliveries"),
			"value": early_deliveries,
			"indicator": "orange"
		},
		{
			"label": _("On-Time Percentage"),
			"value": f"{on_time_percentage:.2f}%",
			"indicator": "green" if on_time_percentage > 90 else "red"
		},
		{
			"label": _("Late Percentage"),
			"value": f"{late_percentage:.2f}%",
			"indicator": "red" if late_percentage > 10 else "green"
		},
		{
			"label": _("Average Delay (min)"),
			"value": f"{avg_delay:.1f}",
			"indicator": "red" if avg_delay > 30 else "orange"
		},
		{
			"label": _("Average Early (min)"),
			"value": f"{avg_early:.1f}",
			"indicator": "green"
		}
	]
