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
			"fieldname": "origin_port",
			"label": _("Origin Port"),
			"fieldtype": "Link",
			"options": "UNLOCO",
			"width": 120
		},
		{
			"fieldname": "destination_port",
			"label": _("Destination Port"),
			"fieldtype": "Link",
			"options": "UNLOCO",
			"width": 120
		},
		{
			"fieldname": "shipping_line",
			"label": _("Shipping Line"),
			"fieldtype": "Link",
			"options": "Shipping Line",
			"width": 120
		},
		{
			"fieldname": "vessel_name",
			"label": _("Vessel"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "etd",
			"label": _("ETD"),
			"fieldtype": "Datetime",
			"width": 150
		},
		{
			"fieldname": "actual_departure",
			"label": _("Actual Departure"),
			"fieldtype": "Datetime",
			"width": 150
		},
		{
			"fieldname": "departure_delay_days",
			"label": _("Departure Delay (Days)"),
			"fieldtype": "Float",
			"precision": 1,
			"width": 140
		},
		{
			"fieldname": "eta",
			"label": _("ETA"),
			"fieldtype": "Datetime",
			"width": 150
		},
		{
			"fieldname": "actual_arrival",
			"label": _("Actual Arrival"),
			"fieldtype": "Datetime",
			"width": 150
		},
		{
			"fieldname": "arrival_delay_days",
			"label": _("Arrival Delay (Days)"),
			"fieldtype": "Float",
			"precision": 1,
			"width": 140
		},
		{
			"fieldname": "on_time_status",
			"label": _("On-Time Status"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "delay_count",
			"label": _("Delay Count"),
			"fieldtype": "Int",
			"width": 100
		}
	]

def get_data(filters):
	conditions = get_conditions(filters)
	
	# Get Sea Shipments with on-time performance data
	data = frappe.db.sql("""
		SELECT
			sship.name as sea_shipment,
			sship.booking_date,
			sship.origin_port,
			sship.destination_port,
			sship.shipping_line,
			sship.vessel_name,
			sship.etd,
			sship.actual_departure,
			CASE 
				WHEN sship.etd IS NOT NULL AND sship.actual_departure IS NOT NULL
				THEN TIMESTAMPDIFF(DAY, sship.etd, sship.actual_departure)
				ELSE NULL
			END as departure_delay_days,
			sship.eta,
			sship.actual_arrival,
			CASE 
				WHEN sship.eta IS NOT NULL AND sship.actual_arrival IS NOT NULL
				THEN TIMESTAMPDIFF(DAY, sship.eta, sship.actual_arrival)
				ELSE NULL
			END as arrival_delay_days,
			CASE 
				WHEN sship.eta IS NOT NULL AND sship.actual_arrival IS NOT NULL
					AND TIMESTAMPDIFF(DAY, sship.eta, sship.actual_arrival) <= 0
				THEN 'On Time'
				WHEN sship.eta IS NOT NULL AND sship.actual_arrival IS NOT NULL
					AND TIMESTAMPDIFF(DAY, sship.eta, sship.actual_arrival) > 0
				THEN 'Delayed'
				ELSE 'Pending'
			END as on_time_status,
			sship.delay_count
		FROM
			`tabSea Shipment` sship
		WHERE
			sship.docstatus = 1
			{conditions}
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
	
	if filters.get("shipping_line"):
		conditions.append("sship.shipping_line = %(shipping_line)s")
	
	if filters.get("on_time_status"):
		if filters.on_time_status == "On Time":
			conditions.append("sship.eta IS NOT NULL AND sship.actual_arrival IS NOT NULL AND TIMESTAMPDIFF(DAY, sship.eta, sship.actual_arrival) <= 0")
		elif filters.on_time_status == "Delayed":
			conditions.append("sship.eta IS NOT NULL AND sship.actual_arrival IS NOT NULL AND TIMESTAMPDIFF(DAY, sship.eta, sship.actual_arrival) > 0")
		elif filters.on_time_status == "Pending":
			conditions.append("(sship.eta IS NULL OR sship.actual_arrival IS NULL)")
	
	return " AND " + " AND ".join(conditions) if conditions else ""

def get_chart_data(data):
	if not data:
		return None
	
	# On-time performance chart
	on_time_count = sum(1 for row in data if row.get("on_time_status") == "On Time")
	delayed_count = sum(1 for row in data if row.get("on_time_status") == "Delayed")
	pending_count = sum(1 for row in data if row.get("on_time_status") == "Pending")
	
	chart = {
		"data": {
			"labels": ["On Time", "Delayed", "Pending"],
			"datasets": [{
				"name": "Shipments",
				"values": [on_time_count, delayed_count, pending_count]
			}]
		},
		"type": "pie",
		"colors": ["#28a745", "#dc3545", "#ffc107"]
	}
	
	return chart

def get_summary(data, filters):
	if not data:
		return []
	
	total_shipments = len(data)
	on_time_count = sum(1 for row in data if row.get("on_time_status") == "On Time")
	delayed_count = sum(1 for row in data if row.get("on_time_status") == "Delayed")
	pending_count = sum(1 for row in data if row.get("on_time_status") == "Pending")
	
	on_time_percentage = (on_time_count / total_shipments * 100) if total_shipments > 0 else 0
	
	avg_departure_delay = sum(flt(row.departure_delay_days or 0) for row in data if row.departure_delay_days) / len([r for r in data if r.departure_delay_days]) if [r for r in data if r.departure_delay_days] else 0
	avg_arrival_delay = sum(flt(row.arrival_delay_days or 0) for row in data if row.arrival_delay_days) / len([r for r in data if r.arrival_delay_days]) if [r for r in data if r.arrival_delay_days] else 0
	
	summary = [
		{
			"label": _("Total Shipments"),
			"value": total_shipments,
			"indicator": "blue"
		},
		{
			"label": _("On-Time Shipments"),
			"value": on_time_count,
			"indicator": "green"
		},
		{
			"label": _("Delayed Shipments"),
			"value": delayed_count,
			"indicator": "red"
		},
		{
			"label": _("Pending Shipments"),
			"value": pending_count,
			"indicator": "orange"
		},
		{
			"label": _("On-Time Performance %"),
			"value": f"{on_time_percentage:.1f}%",
			"indicator": "green" if on_time_percentage >= 90 else "orange" if on_time_percentage >= 75 else "red"
		},
		{
			"label": _("Avg Departure Delay (Days)"),
			"value": f"{avg_departure_delay:.1f}",
			"indicator": "green" if avg_departure_delay <= 0 else "orange" if avg_departure_delay <= 1 else "red"
		},
		{
			"label": _("Avg Arrival Delay (Days)"),
			"value": f"{avg_arrival_delay:.1f}",
			"indicator": "green" if avg_arrival_delay <= 0 else "orange" if avg_arrival_delay <= 1 else "red"
		}
	]
	
	return summary

