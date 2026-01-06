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
			"fieldname": "airline",
			"label": _("Airline"),
			"fieldtype": "Link",
			"options": "Airline",
			"width": 150
		},
		{
			"fieldname": "total_shipments",
			"label": _("Total Shipments"),
			"fieldtype": "Int",
			"width": 120
		},
		{
			"fieldname": "total_weight",
			"label": _("Total Weight (kg)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 130
		},
		{
			"fieldname": "total_volume",
			"label": _("Total Volume (m³)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 130
		},
		{
			"fieldname": "total_chargeable",
			"label": _("Total Chargeable (kg)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 150
		},
		{
			"fieldname": "on_time_shipments",
			"label": _("On-Time Shipments"),
			"fieldtype": "Int",
			"width": 130
		},
		{
			"fieldname": "delayed_shipments",
			"label": _("Delayed Shipments"),
			"fieldtype": "Int",
			"width": 130
		},
		{
			"fieldname": "on_time_percentage",
			"label": _("On-Time %"),
			"fieldtype": "Percent",
			"precision": 1,
			"width": 100
		},
		{
			"fieldname": "avg_departure_delay",
			"label": _("Avg Departure Delay (hrs)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 160
		},
		{
			"fieldname": "avg_arrival_delay",
			"label": _("Avg Arrival Delay (hrs)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 160
		},
		{
			"fieldname": "total_revenue",
			"label": _("Total Revenue"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "avg_revenue_per_shipment",
			"label": _("Avg Revenue/Shipment"),
			"fieldtype": "Currency",
			"width": 150
		}
	]

def get_data(filters):
	conditions = get_conditions(filters)
	
	data = frappe.db.sql("""
		SELECT
			aship.airline,
			COUNT(DISTINCT aship.name) as total_shipments,
			SUM(aship.weight) as total_weight,
			SUM(aship.volume) as total_volume,
			SUM(aship.chargeable) as total_chargeable,
			SUM(CASE WHEN aship.eta IS NOT NULL AND aship.actual_arrival IS NOT NULL 
				AND TIMESTAMPDIFF(HOUR, aship.eta, aship.actual_arrival) <= 0 THEN 1 ELSE 0 END) as on_time_shipments,
			SUM(CASE WHEN aship.eta IS NOT NULL AND aship.actual_arrival IS NOT NULL 
				AND TIMESTAMPDIFF(HOUR, aship.eta, aship.actual_arrival) > 0 THEN 1 ELSE 0 END) as delayed_shipments,
			CASE
				WHEN COUNT(CASE WHEN aship.eta IS NOT NULL AND aship.actual_arrival IS NOT NULL THEN 1 END) > 0
				THEN (SUM(CASE WHEN aship.eta IS NOT NULL AND aship.actual_arrival IS NOT NULL 
					AND TIMESTAMPDIFF(HOUR, aship.eta, aship.actual_arrival) <= 0 THEN 1 ELSE 0 END) * 100.0) /
					COUNT(CASE WHEN aship.eta IS NOT NULL AND aship.actual_arrival IS NOT NULL THEN 1 END)
				ELSE 0
			END as on_time_percentage,
			AVG(CASE WHEN aship.etd IS NOT NULL AND aship.actual_departure IS NOT NULL
				THEN TIMESTAMPDIFF(HOUR, aship.etd, aship.actual_departure)
				ELSE NULL END) as avg_departure_delay,
			AVG(CASE WHEN aship.eta IS NOT NULL AND aship.actual_arrival IS NOT NULL
				THEN TIMESTAMPDIFF(HOUR, aship.eta, aship.actual_arrival)
				ELSE NULL END) as avg_arrival_delay,
			COALESCE(SUM(asc.total_amount), 0) as total_revenue,
			CASE
				WHEN COUNT(DISTINCT aship.name) > 0
				THEN COALESCE(SUM(asc.total_amount), 0) / COUNT(DISTINCT aship.name)
				ELSE 0
			END as avg_revenue_per_shipment
		FROM
			`tabAir Shipment` aship
		LEFT JOIN
			`tabAir Shipment Charges` asc ON asc.parent = aship.name
		WHERE
			aship.docstatus = 1
			AND aship.airline IS NOT NULL
			{conditions}
		GROUP BY
			aship.airline
		ORDER BY
			total_shipments DESC, on_time_percentage DESC
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
	
	return " AND " + " AND ".join(conditions) if conditions else ""

def get_chart_data(data):
	if not data:
		return None
	
	# On-time performance by airline
	top_airlines = sorted(data, key=lambda x: flt(x.get("total_shipments") or 0), reverse=True)[:10]
	
	chart = {
		"data": {
			"labels": [row.get("airline") for row in top_airlines],
			"datasets": [{
				"name": "On-Time %",
				"values": [flt(row.get("on_time_percentage") or 0) for row in top_airlines]
			}]
		},
		"type": "bar",
		"colors": ["#28a745"]
	}
	
	return chart

def get_summary(data, filters):
	if not data:
		return []
	
	total_airlines = len(data)
	total_shipments = sum(flt(row.get("total_shipments") or 0) for row in data)
	total_weight = sum(flt(row.get("total_weight") or 0) for row in data)
	total_revenue = sum(flt(row.get("total_revenue") or 0) for row in data)
	avg_on_time = sum(flt(row.get("on_time_percentage") or 0) for row in data) / total_airlines if total_airlines > 0 else 0
	
	summary = [
		{
			"label": _("Total Airlines"),
			"value": total_airlines,
			"indicator": "blue"
		},
		{
			"label": _("Total Shipments"),
			"value": total_shipments,
			"indicator": "green"
		},
		{
			"label": _("Total Weight (kg)"),
			"value": f"{total_weight:,.2f}",
			"indicator": "blue"
		},
		{
			"label": _("Total Revenue"),
			"value": f"{total_revenue:,.2f}",
			"indicator": "green"
		},
		{
			"label": _("Avg On-Time %"),
			"value": f"{avg_on_time:.1f}%",
			"indicator": "green" if avg_on_time >= 90 else "orange" if avg_on_time >= 75 else "red"
		}
	]
	
	return summary


