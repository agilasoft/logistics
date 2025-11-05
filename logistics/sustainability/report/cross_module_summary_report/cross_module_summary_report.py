# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_months


def execute(filters=None):
	"""Execute Cross Module Summary Report"""
	filters = frappe._dict(filters or {})
	
	# Set default filters
	if not filters.from_date:
		filters.from_date = add_months(getdate(), -12)
	if not filters.to_date:
		filters.to_date = getdate()
	
	# Get data based on filters
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)
	
	return columns, data, None, chart


def get_columns():
	"""Define report columns"""
	return [
		{
			"fieldname": "module",
			"label": _("Module"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "record_count",
			"label": _("Record Count"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "total_energy_consumption",
			"label": _("Total Energy (kWh)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 150
		},
		{
			"fieldname": "total_carbon_footprint",
			"label": _("Total Carbon (kg CO2e)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 160
		},
		{
			"fieldname": "total_waste_generated",
			"label": _("Total Waste (kg)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 130
		},
		{
			"fieldname": "total_water_consumption",
			"label": _("Total Water Consumption"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 150
		},
		{
			"fieldname": "average_sustainability_score",
			"label": _("Avg Sustainability Score"),
			"fieldtype": "Float",
			"precision": 1,
			"width": 160
		},
		{
			"fieldname": "average_renewable_percentage",
			"label": _("Avg Renewable %"),
			"fieldtype": "Percent",
			"precision": 1,
			"width": 130
		}
	]


def get_data(filters):
	"""Get report data"""
	try:
		from logistics.sustainability.api.data_aggregation import get_cross_module_summary
		
		summary = get_cross_module_summary(
			from_date=filters.from_date,
			to_date=filters.to_date
		)
		
		data = []
		module_breakdown = summary.get("module_breakdown", {})
		
		for module, metrics in module_breakdown.items():
			row = {
				"module": module,
				"record_count": summary.get("total_modules", 0),
				"total_energy_consumption": flt(metrics.get("energy_consumption", 0)),
				"total_carbon_footprint": flt(metrics.get("carbon_footprint", 0)),
				"total_waste_generated": flt(metrics.get("waste_generated", 0)),
				"total_water_consumption": flt(metrics.get("water_consumption", 0)),
				"average_sustainability_score": flt(metrics.get("average_sustainability_score", 0)),
				"average_renewable_percentage": flt(metrics.get("average_renewable_percentage", 0))
			}
			data.append(row)
		
		# Add totals row
		if data:
			totals = {
				"module": "Total",
				"record_count": len(data),
				"total_energy_consumption": sum([flt(d.get("total_energy_consumption", 0)) for d in data]),
				"total_carbon_footprint": sum([flt(d.get("total_carbon_footprint", 0)) for d in data]),
				"total_waste_generated": sum([flt(d.get("total_waste_generated", 0)) for d in data]),
				"total_water_consumption": sum([flt(d.get("total_water_consumption", 0)) for d in data]),
				"average_sustainability_score": sum([flt(d.get("average_sustainability_score", 0)) for d in data]) / len(data) if data else 0,
				"average_renewable_percentage": sum([flt(d.get("average_renewable_percentage", 0)) for d in data]) / len(data) if data else 0
			}
			data.append(totals)
		
		return data
	except Exception as e:
		frappe.log_error(f"Error in Cross Module Summary Report: {e}", "Cross Module Summary Report Error")
		return []


def get_chart_data(data):
	"""Generate chart data"""
	if not data or len(data) < 2:  # Exclude totals row
		return None
	
	# Exclude totals row for chart
	chart_data = [d for d in data if d.get("module") != "Total"]
	
	if not chart_data:
		return None
	
	modules = [d.get("module") for d in chart_data]
	carbon_values = [flt(d.get("total_carbon_footprint", 0)) for d in chart_data]
	energy_values = [flt(d.get("total_energy_consumption", 0)) for d in chart_data]
	
	chart = {
		"data": {
			"labels": modules,
			"datasets": [
				{
					"name": "Carbon Footprint (kg CO2e)",
					"values": carbon_values
				},
				{
					"name": "Energy Consumption (kWh)",
					"values": energy_values
				}
			]
		},
		"type": "bar",
		"colors": ["#ff6384", "#36a2eb"]
	}
	
	return chart

