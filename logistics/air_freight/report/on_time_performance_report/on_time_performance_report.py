# Copyright (c) 2025, logistics.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, get_datetime, format_datetime
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
			"fieldname": "airline",
			"label": _("Airline"),
			"fieldtype": "Link",
			"options": "Airline",
			"width": 120
		},
		{
			"fieldname": "etd",
			"label": _("ETD"),
			"fieldtype": "Datetime",
			"width": 130
		},
		{
			"fieldname": "actual_departure",
			"label": _("Actual Departure"),
			"fieldtype": "Datetime",
			"width": 130
		},
		{
			"fieldname": "eta",
			"label": _("ETA"),
			"fieldtype": "Datetime",
			"width": 130
		},
		{
			"fieldname": "actual_arrival",
			"label": _("Actual Arrival"),
			"fieldtype": "Datetime",
			"width": 130
		},
		{
			"fieldname": "departure_delay",
			"label": _("Departure Delay (hrs)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 150
		},
		{
			"fieldname": "arrival_delay",
			"label": _("Arrival Delay (hrs)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 150
		},
		{
			"fieldname": "on_time_status",
			"label": _("On-Time Status"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 120
		}
	]

def get_data(filters):
	conditions = get_conditions(filters)
	
	data = frappe.db.sql("""
		SELECT
			aship.name as air_shipment,
			aship.booking_date,
			aship.origin_port,
			aship.destination_port,
			aship.airline,
			aship.etd,
			aship.actual_departure,
			aship.eta,
			aship.actual_arrival,
			CASE
				WHEN aship.etd IS NOT NULL AND aship.actual_departure IS NOT NULL
				THEN TIMESTAMPDIFF(HOUR, aship.etd, aship.actual_departure)
				ELSE NULL
			END as departure_delay,
			CASE
				WHEN aship.eta IS NOT NULL AND aship.actual_arrival IS NOT NULL
				THEN TIMESTAMPDIFF(HOUR, aship.eta, aship.actual_arrival)
				ELSE NULL
			END as arrival_delay,
			CASE
				WHEN aship.eta IS NOT NULL AND aship.actual_arrival IS NOT NULL THEN
					CASE
						WHEN TIMESTAMPDIFF(HOUR, aship.eta, aship.actual_arrival) <= 0 THEN 'On Time'
						WHEN TIMESTAMPDIFF(HOUR, aship.eta, aship.actual_arrival) <= 24 THEN 'Delayed < 24hrs'
						ELSE 'Delayed > 24hrs'
					END
				ELSE 'Pending'
			END as on_time_status,
			aship.status
		FROM
			`tabAir Shipment` aship
		WHERE
			aship.docstatus = 1
			{conditions}
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
	
	if filters.get("airline"):
		conditions.append("aship.airline = %(airline)s")
	
	if filters.get("on_time_status"):
		if filters.get("on_time_status") == "On Time":
			conditions.append("TIMESTAMPDIFF(HOUR, aship.eta, aship.actual_arrival) <= 0")
		elif filters.get("on_time_status") == "Delayed":
			conditions.append("TIMESTAMPDIFF(HOUR, aship.eta, aship.actual_arrival) > 0")
	
	return " AND " + " AND ".join(conditions) if conditions else ""

def get_chart_data(data):
	if not data:
		return None
	
	# On-time performance chart
	performance_count = {
		"On Time": 0,
		"Delayed < 24hrs": 0,
		"Delayed > 24hrs": 0,
		"Pending": 0
	}
	
	for row in data:
		status = row.get("on_time_status") or "Pending"
		performance_count[status] = performance_count.get(status, 0) + 1
	
	chart = {
		"data": {
			"labels": list(performance_count.keys()),
			"datasets": [{
				"name": "On-Time Performance",
				"values": list(performance_count.values())
			}]
		},
		"type": "pie",
		"colors": ["#28a745", "#ffa00a", "#ff5858", "#7cd6fd"]
	}
	
	return chart

def get_summary(data, filters):
	if not data:
		return []
	
	total_shipments = len(data)
	on_time = sum(1 for row in data if row.get("on_time_status") == "On Time")
	delayed = sum(1 for row in data if row.get("on_time_status") in ["Delayed < 24hrs", "Delayed > 24hrs"])
	pending = sum(1 for row in data if row.get("on_time_status") == "Pending")
	on_time_percentage = (on_time / total_shipments * 100) if total_shipments > 0 else 0
	
	avg_departure_delay = sum(flt(row.get("departure_delay") or 0) for row in data if row.get("departure_delay")) / max(1, sum(1 for row in data if row.get("departure_delay")))
	avg_arrival_delay = sum(flt(row.get("arrival_delay") or 0) for row in data if row.get("arrival_delay")) / max(1, sum(1 for row in data if row.get("arrival_delay")))
	
	summary = [
		{
			"label": _("Total Shipments"),
			"value": total_shipments,
			"indicator": "blue"
		},
		{
			"label": _("On Time"),
			"value": on_time,
			"indicator": "green"
		},
		{
			"label": _("Delayed"),
			"value": delayed,
			"indicator": "red"
		},
		{
			"label": _("Pending"),
			"value": pending,
			"indicator": "orange"
		},
		{
			"label": _("On-Time %"),
			"value": f"{on_time_percentage:.1f}%",
			"indicator": "green" if on_time_percentage >= 90 else "orange" if on_time_percentage >= 75 else "red"
		},
		{
			"label": _("Avg Departure Delay (hrs)"),
			"value": f"{avg_departure_delay:.1f}",
			"indicator": "green" if avg_departure_delay <= 0 else "orange" if avg_departure_delay <= 2 else "red"
		},
		{
			"label": _("Avg Arrival Delay (hrs)"),
			"value": f"{avg_arrival_delay:.1f}",
			"indicator": "green" if avg_arrival_delay <= 0 else "orange" if avg_arrival_delay <= 2 else "red"
		}
	]
	
	return summary


