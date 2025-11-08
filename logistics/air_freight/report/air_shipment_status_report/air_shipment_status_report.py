# Copyright (c) 2025, logistics.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, format_datetime
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
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "local_customer",
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
			"fieldname": "etd",
			"label": _("ETD"),
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
			"fieldname": "weight",
			"label": _("Weight (kg)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 100
		},
		{
			"fieldname": "volume",
			"label": _("Volume (m³)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 100
		},
		{
			"fieldname": "chargeable",
			"label": _("Chargeable (kg)"),
			"fieldtype": "Float",
			"precision": 2,
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
			"fieldname": "billing_status",
			"label": _("Billing Status"),
			"fieldtype": "Data",
			"width": 120
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
			aship.status,
			aship.local_customer,
			aship.origin_port,
			aship.destination_port,
			aship.etd,
			aship.eta,
			aship.weight,
			aship.volume,
			aship.chargeable,
			aship.airline,
			aship.billing_status,
			aship.company
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
	
	if filters.get("status"):
		conditions.append("aship.status = %(status)s")
	
	if filters.get("company"):
		conditions.append("aship.company = %(company)s")
	
	if filters.get("customer"):
		conditions.append("aship.local_customer = %(customer)s")
	
	if filters.get("airline"):
		conditions.append("aship.airline = %(airline)s")
	
	if filters.get("billing_status"):
		conditions.append("aship.billing_status = %(billing_status)s")
	
	return " AND " + " AND ".join(conditions) if conditions else ""

def get_chart_data(data):
	if not data:
		return None
	
	# Status distribution chart
	status_count = {}
	for row in data:
		status = row.get("status") or "Unknown"
		status_count[status] = status_count.get(status, 0) + 1
	
	chart = {
		"data": {
			"labels": list(status_count.keys()),
			"datasets": [{
				"name": "Shipments by Status",
				"values": list(status_count.values())
			}]
		},
		"type": "pie",
		"colors": ["#7cd6fd", "#5e64ff", "#743ee2", "#ff5858", "#ffa00a", "#28a745"]
	}
	
	return chart

def get_summary(data, filters):
	if not data:
		return []
	
	total_shipments = len(data)
	total_weight = sum(flt(row.get("weight") or 0) for row in data)
	total_volume = sum(flt(row.get("volume") or 0) for row in data)
	total_chargeable = sum(flt(row.get("chargeable") or 0) for row in data)
	
	# Count by status
	status_counts = {}
	for row in data:
		status = row.get("status") or "Unknown"
		status_counts[status] = status_counts.get(status, 0) + 1
	
	summary = [
		{
			"label": _("Total Shipments"),
			"value": total_shipments,
			"indicator": "blue"
		},
		{
			"label": _("Total Weight (kg)"),
			"value": f"{total_weight:,.2f}",
			"indicator": "green"
		},
		{
			"label": _("Total Volume (m³)"),
			"value": f"{total_volume:,.2f}",
			"indicator": "blue"
		},
		{
			"label": _("Total Chargeable (kg)"),
			"value": f"{total_chargeable:,.2f}",
			"indicator": "orange"
		}
	]
	
	return summary


