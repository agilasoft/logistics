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
			"fieldname": "port_charges",
			"label": _("Port Charges"),
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
			"fieldname": "detention_demurrage",
			"label": _("Detention/Demurrage"),
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
	
	# Get Sea Shipments with cost breakdown from charges
	data = frappe.db.sql("""
		SELECT
			sship.name as sea_shipment,
			sship.booking_date,
			sship.origin_port,
			sship.destination_port,
			sship.shipping_line,
			sship.vessel_name,
			sship.chargeable,
			COALESCE(SUM(CASE WHEN sfc.charge_type = 'Freight' THEN sfc.total_amount ELSE 0 END), 0) as freight_cost,
			COALESCE(SUM(CASE WHEN sfc.charge_type = 'Fuel Surcharge' THEN sfc.total_amount ELSE 0 END), 0) as fuel_surcharge,
			COALESCE(SUM(CASE WHEN sfc.charge_type IN ('Handling', 'Terminal Handling') THEN sfc.total_amount ELSE 0 END), 0) as handling_cost,
			COALESCE(SUM(CASE WHEN sfc.charge_type = 'Port Charges' THEN sfc.total_amount ELSE 0 END), 0) as port_charges,
			COALESCE(SUM(CASE WHEN sfc.charge_type = 'Customs Clearance' THEN sfc.total_amount ELSE 0 END), 0) as customs_cost,
			COALESCE(SUM(CASE WHEN sfc.charge_type IN ('Detention', 'Demurrage') THEN sfc.total_amount ELSE 0 END), 0) as detention_demurrage,
			COALESCE(SUM(CASE WHEN sfc.charge_type NOT IN ('Freight', 'Fuel Surcharge', 'Handling', 'Terminal Handling', 'Port Charges', 'Customs Clearance', 'Detention', 'Demurrage') THEN sfc.total_amount ELSE 0 END), 0) as other_costs,
			COALESCE(SUM(sfc.total_amount), 0) as total_cost,
			CASE 
				WHEN sship.chargeable > 0 THEN COALESCE(SUM(sfc.total_amount), 0) / sship.chargeable
				ELSE 0
			END as cost_per_kg,
			sship.company
		FROM
			`tabSea Shipment` sship
		LEFT JOIN
			`tabSea Freight Charges` sfc ON sfc.parent = sship.name
		WHERE
			sship.docstatus = 1
			{conditions}
		GROUP BY
			sship.name
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
	
	if filters.get("origin_port"):
		conditions.append("sship.origin_port = %(origin_port)s")
	
	if filters.get("destination_port"):
		conditions.append("sship.destination_port = %(destination_port)s")
	
	return " AND " + " AND ".join(conditions) if conditions else ""

def get_chart_data(data):
	if not data:
		return None
	
	# Cost breakdown by category
	cost_categories = {
		"Freight": 0,
		"Fuel Surcharge": 0,
		"Handling": 0,
		"Port Charges": 0,
		"Customs": 0,
		"Detention/Demurrage": 0,
		"Other": 0
	}
	
	for row in data:
		cost_categories["Freight"] += flt(row.get("freight_cost") or 0)
		cost_categories["Fuel Surcharge"] += flt(row.get("fuel_surcharge") or 0)
		cost_categories["Handling"] += flt(row.get("handling_cost") or 0)
		cost_categories["Port Charges"] += flt(row.get("port_charges") or 0)
		cost_categories["Customs"] += flt(row.get("customs_cost") or 0)
		cost_categories["Detention/Demurrage"] += flt(row.get("detention_demurrage") or 0)
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
		"colors": ["#5e64ff", "#743ee2", "#ff5858", "#ffa00a", "#28a745", "#ffc107", "#17a2b8"]
	}
	
	return chart

def get_summary(data, filters):
	if not data:
		return []
	
	total_shipments = len(data)
	total_cost = sum(flt(row.get("total_cost") or 0) for row in data)
	total_freight = sum(flt(row.get("freight_cost") or 0) for row in data)
	total_fuel = sum(flt(row.get("fuel_surcharge") or 0) for row in data)
	total_penalties = sum(flt(row.get("detention_demurrage") or 0) for row in data)
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
			"label": _("Detention/Demurrage"),
			"value": f"{total_penalties:,.2f}",
			"indicator": "red" if total_penalties > 0 else "green"
		},
		{
			"label": _("Avg Cost per kg"),
			"value": f"{avg_cost_per_kg:,.2f}",
			"indicator": "red"
		}
	]
	
	return summary

