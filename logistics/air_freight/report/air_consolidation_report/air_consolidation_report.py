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
			"fieldname": "consolidation",
			"label": _("Consolidation"),
			"fieldtype": "Link",
			"options": "Air Consolidation",
			"width": 150
		},
		{
			"fieldname": "consolidation_date",
			"label": _("Consolidation Date"),
			"fieldtype": "Date",
			"width": 120
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "origin_airport",
			"label": _("Origin"),
			"fieldtype": "Link",
			"options": "UNLOCO",
			"width": 120
		},
		{
			"fieldname": "destination_airport",
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
			"fieldname": "total_packages",
			"label": _("Total Packages"),
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
			"fieldname": "chargeable_weight",
			"label": _("Chargeable (kg)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 130
		},
		{
			"fieldname": "consolidation_ratio",
			"label": _("Consolidation Ratio"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 140
		},
		{
			"fieldname": "cost_per_kg",
			"label": _("Cost per kg"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "departure_date",
			"label": _("Departure Date"),
			"fieldtype": "Date",
			"width": 120
		},
		{
			"fieldname": "arrival_date",
			"label": _("Arrival Date"),
			"fieldtype": "Date",
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
			ac.name as consolidation,
			ac.consolidation_date,
			ac.status,
			ac.origin_airport,
			ac.destination_airport,
			ac.total_packages as total_shipments,
			ac.total_packages,
			ac.total_weight,
			ac.total_volume,
			ac.chargeable_weight as chargeable_weight,
			ac.consolidation_ratio,
			ac.cost_per_kg,
			ac.departure_date,
			ac.arrival_date,
			ac.company
		FROM
			`tabAir Consolidation` ac
		WHERE
			ac.docstatus = 1
			{conditions}
		ORDER BY
			ac.consolidation_date DESC, ac.name DESC
	""".format(conditions=conditions), filters, as_dict=1)
	
	return data

def get_conditions(filters):
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("ac.consolidation_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("ac.consolidation_date <= %(to_date)s")
	
	if filters.get("status"):
		conditions.append("ac.status = %(status)s")
	
	if filters.get("company"):
		conditions.append("ac.company = %(company)s")
	
	if filters.get("origin_airport"):
		conditions.append("ac.origin_airport = %(origin_airport)s")
	
	if filters.get("destination_airport"):
		conditions.append("ac.destination_airport = %(destination_airport)s")
	
	return " AND " + " AND ".join(conditions) if conditions else ""

def get_chart_data(data):
	if not data:
		return None
	
	# Consolidation ratio chart
	ratio_ranges = {
		"< 1.0": 0,
		"1.0 - 1.5": 0,
		"1.5 - 2.0": 0,
		"> 2.0": 0
	}
	
	for row in data:
		ratio = flt(row.get("consolidation_ratio") or 0)
		if ratio < 1.0:
			ratio_ranges["< 1.0"] += 1
		elif ratio < 1.5:
			ratio_ranges["1.0 - 1.5"] += 1
		elif ratio < 2.0:
			ratio_ranges["1.5 - 2.0"] += 1
		else:
			ratio_ranges["> 2.0"] += 1
	
	chart = {
		"data": {
			"labels": list(ratio_ranges.keys()),
			"datasets": [{
				"name": "Consolidations by Ratio",
				"values": list(ratio_ranges.values())
			}]
		},
		"type": "bar",
		"colors": ["#5e64ff", "#743ee2", "#ff5858", "#ffa00a"]
	}
	
	return chart

def get_summary(data, filters):
	if not data:
		return []
	
	total_consolidations = len(data)
	total_shipments = sum(flt(row.get("total_shipments") or 0) for row in data)
	total_weight = sum(flt(row.get("total_weight") or 0) for row in data)
	total_volume = sum(flt(row.get("total_volume") or 0) for row in data)
	avg_ratio = sum(flt(row.get("consolidation_ratio") or 0) for row in data) / total_consolidations if total_consolidations > 0 else 0
	
	summary = [
		{
			"label": _("Total Consolidations"),
			"value": total_consolidations,
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
			"label": _("Total Volume (m³)"),
			"value": f"{total_volume:,.2f}",
			"indicator": "green"
		},
		{
			"label": _("Avg Consolidation Ratio"),
			"value": f"{avg_ratio:,.2f}",
			"indicator": "orange"
		}
	]
	
	return summary


