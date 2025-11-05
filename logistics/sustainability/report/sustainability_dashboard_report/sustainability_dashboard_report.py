# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_months


def execute(filters=None):
	"""Execute Sustainability Dashboard Report"""
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
			"width": 120
		},
		{
			"fieldname": "branch",
			"label": _("Branch"),
			"fieldtype": "Link",
			"options": "Branch",
			"width": 120
		},
		{
			"fieldname": "facility",
			"label": _("Facility"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "total_records",
			"label": _("Total Records"),
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
			"fieldname": "average_sustainability_score",
			"label": _("Avg Sustainability Score"),
			"fieldtype": "Float",
			"precision": 1,
			"width": 170
		},
		{
			"fieldname": "average_energy_efficiency",
			"label": _("Avg Energy Efficiency"),
			"fieldtype": "Float",
			"precision": 1,
			"width": 150
		},
		{
			"fieldname": "average_carbon_efficiency",
			"label": _("Avg Carbon Efficiency"),
			"fieldtype": "Float",
			"precision": 1,
			"width": 150
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
		from logistics.sustainability.doctype.sustainability_metrics.sustainability_metrics import get_sustainability_dashboard_data
		
		dashboard_data = get_sustainability_dashboard_data(
			module=filters.module,
			branch=filters.branch,
			facility=filters.facility,
			from_date=filters.from_date,
			to_date=filters.to_date
		)
		
		summary = dashboard_data.get("summary", {})
		metrics = dashboard_data.get("metrics", [])
		
		# Group by module/branch/facility
		grouped_data = {}
		for metric in metrics:
			key = f"{metric.module or 'All'}_{metric.branch or 'All'}_{metric.facility or 'All'}"
			if key not in grouped_data:
				grouped_data[key] = {
					"module": metric.module,
					"branch": metric.branch,
					"facility": metric.facility,
					"total_records": 0,
					"total_energy": 0,
					"total_carbon": 0,
					"total_waste": 0,
					"total_score": 0,
					"total_energy_efficiency": 0,
					"total_carbon_efficiency": 0,
					"total_renewable": 0
				}
			
			grouped_data[key]["total_records"] += 1
			grouped_data[key]["total_energy"] += flt(metric.energy_consumption)
			grouped_data[key]["total_carbon"] += flt(metric.carbon_footprint)
			grouped_data[key]["total_waste"] += flt(metric.waste_generated)
			grouped_data[key]["total_score"] += flt(metric.sustainability_score)
			grouped_data[key]["total_energy_efficiency"] += flt(metric.energy_efficiency_score)
			grouped_data[key]["total_carbon_efficiency"] += flt(metric.carbon_efficiency_score)
			grouped_data[key]["total_renewable"] += flt(metric.renewable_energy_percentage)
		
		# Format data
		data = []
		for key, group in grouped_data.items():
			record_count = group["total_records"] or 1
			row = {
				"module": group["module"],
				"branch": group["branch"],
				"facility": group["facility"],
				"total_records": group["total_records"],
				"total_energy_consumption": group["total_energy"],
				"total_carbon_footprint": group["total_carbon"],
				"total_waste_generated": group["total_waste"],
				"average_sustainability_score": group["total_score"] / record_count,
				"average_energy_efficiency": group["total_energy_efficiency"] / record_count,
				"average_carbon_efficiency": group["total_carbon_efficiency"] / record_count,
				"average_renewable_percentage": group["total_renewable"] / record_count
			}
			data.append(row)
		
		return data
	except Exception as e:
		frappe.log_error(f"Error in Sustainability Dashboard Report: {e}", "Sustainability Dashboard Report Error")
		return []


def get_chart_data(data):
	"""Generate chart data"""
	if not data:
		return None
	
	# Group by module for comparison
	module_data = {}
	for record in data:
		module = record.get("module") or "All"
		if module not in module_data:
			module_data[module] = {
				"carbon": 0,
				"energy": 0,
				"score": 0,
				"count": 0
			}
		module_data[module]["carbon"] += flt(record.get("total_carbon_footprint", 0))
		module_data[module]["energy"] += flt(record.get("total_energy_consumption", 0))
		module_data[module]["score"] += flt(record.get("average_sustainability_score", 0))
		module_data[module]["count"] += 1
	
	modules = list(module_data.keys())
	carbon_values = [module_data[m]["carbon"] for m in modules]
	energy_values = [module_data[m]["energy"] for m in modules]
	score_values = [module_data[m]["score"] / module_data[m]["count"] if module_data[m]["count"] > 0 else 0 for m in modules]
	
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
				},
				{
					"name": "Sustainability Score",
					"values": score_values
				}
			]
		},
		"type": "bar",
		"colors": ["#ff6384", "#36a2eb", "#4bc0c0"]
	}
	
	return chart

