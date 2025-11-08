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
			"fieldname": "container_type",
			"label": _("Container Type"),
			"fieldtype": "Link",
			"options": "Container Type",
			"width": 150
		},
		{
			"fieldname": "container_size",
			"label": _("Size"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "total_containers",
			"label": _("Total Containers"),
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
			"precision": 3,
			"width": 130
		},
		{
			"fieldname": "max_weight",
			"label": _("Max Weight (kg)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 130
		},
		{
			"fieldname": "max_volume",
			"label": _("Max Volume (m³)"),
			"fieldtype": "Float",
			"precision": 3,
			"width": 130
		},
		{
			"fieldname": "weight_utilization",
			"label": _("Weight Utilization %"),
			"fieldtype": "Percent",
			"precision": 2,
			"width": 140
		},
		{
			"fieldname": "volume_utilization",
			"label": _("Volume Utilization %"),
			"fieldtype": "Percent",
			"precision": 2,
			"width": 140
		},
		{
			"fieldname": "avg_utilization",
			"label": _("Avg Utilization %"),
			"fieldtype": "Percent",
			"precision": 2,
			"width": 140
		}
	]

def get_data(filters):
	conditions = get_conditions(filters)
	
	# Get container utilization data
	data = frappe.db.sql("""
		SELECT
			sfc.type as container_type,
			sfc.size as container_size,
			COUNT(*) as total_containers,
			COALESCE(SUM(sship.total_weight), 0) as total_weight,
			COALESCE(SUM(sship.total_volume), 0) as total_volume,
			COALESCE(MAX(ct.max_weight), 0) as max_weight,
			COALESCE(MAX(ct.max_volume), 0) as max_volume
		FROM
			`tabSea Freight Containers` sfc
		INNER JOIN
			`tabSea Shipment` sship ON sfc.parent = sship.name
		LEFT JOIN
			`tabContainer Type` ct ON sfc.type = ct.name
		WHERE
			sship.docstatus = 1
			{conditions}
		GROUP BY
			sfc.type, sfc.size
		ORDER BY
			sfc.type, sfc.size
	""".format(conditions=conditions), filters, as_dict=1)
	
	# Calculate utilization percentages
	for row in data:
		if row.max_weight and row.max_weight > 0:
			row.weight_utilization = (row.total_weight / (row.max_weight * row.total_containers)) * 100 if row.total_containers > 0 else 0
		else:
			row.weight_utilization = 0
		
		if row.max_volume and row.max_volume > 0:
			row.volume_utilization = (row.total_volume / (row.max_volume * row.total_containers)) * 100 if row.total_containers > 0 else 0
		else:
			row.volume_utilization = 0
		
		row.avg_utilization = (row.weight_utilization + row.volume_utilization) / 2
	
	return data

def get_conditions(filters):
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("sship.booking_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("sship.booking_date <= %(to_date)s")
	
	if filters.get("company"):
		conditions.append("sship.company = %(company)s")
	
	if filters.get("container_type"):
		conditions.append("sfc.type = %(container_type)s")
	
	return " AND " + " AND ".join(conditions) if conditions else ""

def get_chart_data(data):
	if not data:
		return None
	
	# Utilization by container type
	chart = {
		"data": {
			"labels": [f"{row.container_type} ({row.container_size})" for row in data],
			"datasets": [{
				"name": "Weight Utilization %",
				"values": [flt(row.weight_utilization) for row in data]
			}, {
				"name": "Volume Utilization %",
				"values": [flt(row.volume_utilization) for row in data]
			}]
		},
		"type": "bar",
		"colors": ["#5e64ff", "#743ee2"]
	}
	
	return chart

def get_summary(data, filters):
	if not data:
		return []
	
	total_containers = sum(row.total_containers for row in data)
	total_weight = sum(flt(row.total_weight) for row in data)
	total_volume = sum(flt(row.total_volume) for row in data)
	avg_weight_util = sum(flt(row.weight_utilization) for row in data) / len(data) if data else 0
	avg_volume_util = sum(flt(row.volume_utilization) for row in data) / len(data) if data else 0
	avg_utilization = (avg_weight_util + avg_volume_util) / 2
	
	summary = [
		{
			"label": _("Total Containers"),
			"value": total_containers,
			"indicator": "blue"
		},
		{
			"label": _("Total Weight (kg)"),
			"value": f"{total_weight:,.2f}",
			"indicator": "blue"
		},
		{
			"label": _("Total Volume (m³)"),
			"value": f"{total_volume:,.2f}",
			"indicator": "blue"
		},
		{
			"label": _("Avg Weight Utilization %"),
			"value": f"{avg_weight_util:.1f}%",
			"indicator": "green" if avg_weight_util >= 80 else "orange" if avg_weight_util >= 60 else "red"
		},
		{
			"label": _("Avg Volume Utilization %"),
			"value": f"{avg_volume_util:.1f}%",
			"indicator": "green" if avg_volume_util >= 80 else "orange" if avg_volume_util >= 60 else "red"
		},
		{
			"label": _("Avg Utilization %"),
			"value": f"{avg_utilization:.1f}%",
			"indicator": "green" if avg_utilization >= 80 else "orange" if avg_utilization >= 60 else "red"
		}
	]
	
	return summary

