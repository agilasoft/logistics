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
			"fieldname": "route",
			"label": _("Route"),
			"fieldtype": "Data",
			"width": 200
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
			"fieldname": "total_revenue",
			"label": _("Total Revenue"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "avg_revenue_per_kg",
			"label": _("Avg Revenue/kg"),
			"fieldtype": "Currency",
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
			"fieldname": "top_airline",
			"label": _("Top Airline"),
			"fieldtype": "Link",
			"options": "Airline",
			"width": 120
		}
	]

def get_data(filters):
	conditions = get_conditions(filters)
	
	data = frappe.db.sql("""
		SELECT
			CONCAT(aship.origin_port, ' → ', aship.destination_port) as route,
			aship.origin_port,
			aship.destination_port,
			COUNT(DISTINCT aship.name) as total_shipments,
			SUM(aship.weight) as total_weight,
			SUM(aship.volume) as total_volume,
			SUM(aship.chargeable) as total_chargeable,
			COALESCE(SUM(asc.total_amount), 0) as total_revenue,
			CASE
				WHEN SUM(aship.chargeable) > 0 THEN COALESCE(SUM(asc.total_amount), 0) / SUM(aship.chargeable)
				ELSE 0
			END as avg_revenue_per_kg,
			CASE
				WHEN COUNT(CASE WHEN aship.eta IS NOT NULL AND aship.actual_arrival IS NOT NULL THEN 1 END) > 0
				THEN (SUM(CASE WHEN aship.eta IS NOT NULL AND aship.actual_arrival IS NOT NULL 
					AND TIMESTAMPDIFF(HOUR, aship.eta, aship.actual_arrival) <= 0 THEN 1 ELSE 0 END) * 100.0) /
					COUNT(CASE WHEN aship.eta IS NOT NULL AND aship.actual_arrival IS NOT NULL THEN 1 END)
				ELSE 0
			END as on_time_percentage,
			(
				SELECT airline
				FROM `tabAir Shipment`
				WHERE origin_port = aship.origin_port
				AND destination_port = aship.destination_port
				AND docstatus = 1
				AND airline IS NOT NULL
				GROUP BY airline
				ORDER BY COUNT(*) DESC
				LIMIT 1
			) as top_airline
		FROM
			`tabAir Shipment` aship
		LEFT JOIN
			`tabAir Shipment Charges` asc ON asc.parent = aship.name
		WHERE
			aship.docstatus = 1
			{conditions}
		GROUP BY
			aship.origin_port, aship.destination_port
		ORDER BY
			total_shipments DESC, total_revenue DESC
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
	
	if filters.get("origin_port"):
		conditions.append("aship.origin_port = %(origin_port)s")
	
	if filters.get("destination_port"):
		conditions.append("aship.destination_port = %(destination_port)s")
	
	return " AND " + " AND ".join(conditions) if conditions else ""

def get_chart_data(data):
	if not data:
		return None
	
	# Top routes by revenue
	top_routes = sorted(data, key=lambda x: flt(x.get("total_revenue") or 0), reverse=True)[:10]
	
	chart = {
		"data": {
			"labels": [row.get("route") for row in top_routes],
			"datasets": [{
				"name": "Revenue by Route",
				"values": [flt(row.get("total_revenue") or 0) for row in top_routes]
			}]
		},
		"type": "bar",
		"colors": ["#5e64ff"]
	}
	
	return chart

def get_summary(data, filters):
	if not data:
		return []
	
	total_routes = len(data)
	total_shipments = sum(flt(row.get("total_shipments") or 0) for row in data)
	total_weight = sum(flt(row.get("total_weight") or 0) for row in data)
	total_revenue = sum(flt(row.get("total_revenue") or 0) for row in data)
	avg_on_time = sum(flt(row.get("on_time_percentage") or 0) for row in data) / total_routes if total_routes > 0 else 0
	
	summary = [
		{
			"label": _("Total Routes"),
			"value": total_routes,
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


