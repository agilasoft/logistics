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
			"fieldname": "chargeable",
			"label": _("Chargeable (kg)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 120
		},
		{
			"fieldname": "freight_cost",
			"label": _("Freight Cost"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "fuel_surcharge",
			"label": _("Fuel Surcharge"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "handling_cost",
			"label": _("Handling Cost"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "customs_cost",
			"label": _("Customs Cost"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "other_costs",
			"label": _("Other Costs"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "total_cost",
			"label": _("Total Cost"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "cost_per_kg",
			"label": _("Cost per kg"),
			"fieldtype": "Currency",
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
	
	# Get Air Shipments with cost breakdown from charges
	data = frappe.db.sql("""
		SELECT
			aship.name as air_shipment,
			aship.booking_date,
			aship.origin_port,
			aship.destination_port,
			aship.airline,
			aship.chargeable,
			COALESCE(SUM(CASE WHEN asc.charge_type = 'Freight' THEN asc.total_amount ELSE 0 END), 0) as freight_cost,
			COALESCE(SUM(CASE WHEN asc.charge_type = 'Fuel Surcharge' THEN asc.total_amount ELSE 0 END), 0) as fuel_surcharge,
			COALESCE(SUM(CASE WHEN asc.charge_type IN ('Handling', 'Terminal Handling') THEN asc.total_amount ELSE 0 END), 0) as handling_cost,
			COALESCE(SUM(CASE WHEN asc.charge_type = 'Customs Clearance' THEN asc.total_amount ELSE 0 END), 0) as customs_cost,
			COALESCE(SUM(CASE WHEN asc.charge_type NOT IN ('Freight', 'Fuel Surcharge', 'Handling', 'Terminal Handling', 'Customs Clearance') THEN asc.total_amount ELSE 0 END), 0) as other_costs,
			COALESCE(SUM(asc.total_amount), 0) as total_cost,
			CASE 
				WHEN aship.chargeable > 0 THEN COALESCE(SUM(asc.total_amount), 0) / aship.chargeable
				ELSE 0
			END as cost_per_kg,
			aship.company
		FROM
			`tabAir Shipment` aship
		LEFT JOIN
			`tabAir Shipment Charges` asc ON asc.parent = aship.name
		WHERE
			aship.docstatus = 1
			{conditions}
		GROUP BY
			aship.name
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
	
	if filters.get("origin_port"):
		conditions.append("aship.origin_port = %(origin_port)s")
	
	if filters.get("destination_port"):
		conditions.append("aship.destination_port = %(destination_port)s")
	
	return " AND " + " AND ".join(conditions) if conditions else ""

def get_chart_data(data):
	if not data:
		return None
	
	# Cost breakdown by category
	cost_categories = {
		"Freight": 0,
		"Fuel Surcharge": 0,
		"Handling": 0,
		"Customs": 0,
		"Other": 0
	}
	
	for row in data:
		cost_categories["Freight"] += flt(row.get("freight_cost") or 0)
		cost_categories["Fuel Surcharge"] += flt(row.get("fuel_surcharge") or 0)
		cost_categories["Handling"] += flt(row.get("handling_cost") or 0)
		cost_categories["Customs"] += flt(row.get("customs_cost") or 0)
		cost_categories["Other"] += flt(row.get("other_costs") or 0)
	
	chart = {
		"data": {
			"labels": list(cost_categories.keys()),
			"datasets": [{
				"name": "Cost by Category",
				"values": list(cost_categories.values())
			}]
		},
		"type": "pie",
		"colors": ["#5e64ff", "#743ee2", "#ff5858", "#ffa00a", "#28a745"]
	}
	
	return chart

def get_summary(data, filters):
	if not data:
		return []
	
	total_shipments = len(data)
	total_cost = sum(flt(row.get("total_cost") or 0) for row in data)
	total_freight = sum(flt(row.get("freight_cost") or 0) for row in data)
	total_fuel = sum(flt(row.get("fuel_surcharge") or 0) for row in data)
	total_chargeable = sum(flt(row.get("chargeable") or 0) for row in data)
	avg_cost_per_kg = total_cost / total_chargeable if total_chargeable > 0 else 0
	
	summary = [
		{
			"label": _("Total Shipments"),
			"value": total_shipments,
			"indicator": "blue"
		},
		{
			"label": _("Total Cost"),
			"value": f"{total_cost:,.2f}",
			"indicator": "red"
		},
		{
			"label": _("Freight Cost"),
			"value": f"{total_freight:,.2f}",
			"indicator": "blue"
		},
		{
			"label": _("Fuel Surcharge"),
			"value": f"{total_fuel:,.2f}",
			"indicator": "orange"
		},
		{
			"label": _("Avg Cost per kg"),
			"value": f"{avg_cost_per_kg:,.2f}",
			"indicator": "red"
		}
	]
	
	return summary


