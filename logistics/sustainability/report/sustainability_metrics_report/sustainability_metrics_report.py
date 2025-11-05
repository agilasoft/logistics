# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_months


def execute(filters=None):
	"""Execute Sustainability Metrics Report"""
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
			"fieldname": "date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 100
		},
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
			"fieldname": "energy_consumption",
			"label": _("Energy Consumption (kWh)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 150
		},
		{
			"fieldname": "carbon_footprint",
			"label": _("Carbon Footprint (kg CO2e)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 160
		},
		{
			"fieldname": "waste_generated",
			"label": _("Waste Generated (kg)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 140
		},
		{
			"fieldname": "water_consumption",
			"label": _("Water Consumption"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 130
		},
		{
			"fieldname": "renewable_energy_percentage",
			"label": _("Renewable Energy %"),
			"fieldtype": "Percent",
			"precision": 1,
			"width": 130
		},
		{
			"fieldname": "sustainability_score",
			"label": _("Sustainability Score"),
			"fieldtype": "Float",
			"precision": 1,
			"width": 140
		}
	]


def get_data(filters):
	"""Get report data"""
	
	# Build filters
	report_filters = {}
	if filters.company:
		report_filters["company"] = filters.company
	if filters.module:
		report_filters["module"] = filters.module
	if filters.branch:
		report_filters["branch"] = filters.branch
	if filters.facility:
		report_filters["facility"] = filters.facility
	
	# Handle date range filtering
	if filters.from_date and filters.to_date:
		report_filters["date"] = ["between", [filters.from_date, filters.to_date]]
	elif filters.from_date:
		report_filters["date"] = [">=", filters.from_date]
	elif filters.to_date:
		report_filters["date"] = ["<=", filters.to_date]
	
	# Get sustainability metrics data
	metrics = frappe.get_all("Sustainability Metrics",
		filters=report_filters,
		fields=["name", "date", "module", "branch", "facility", "energy_consumption",
				"carbon_footprint", "waste_generated", "water_consumption",
				"renewable_energy_percentage", "sustainability_score",
				"energy_efficiency_score", "carbon_efficiency_score"],
		order_by="date desc, module, branch"
	)
	
	# Format data for report
	data = []
	for metric in metrics:
		row = {
			"date": metric.date,
			"module": metric.module,
			"branch": metric.branch,
			"facility": metric.facility,
			"energy_consumption": flt(metric.energy_consumption),
			"carbon_footprint": flt(metric.carbon_footprint),
			"waste_generated": flt(metric.waste_generated),
			"water_consumption": flt(metric.water_consumption),
			"renewable_energy_percentage": flt(metric.renewable_energy_percentage),
			"sustainability_score": flt(metric.sustainability_score)
		}
		data.append(row)
	
	return data


def get_chart_data(data):
	"""Generate chart data"""
	if not data:
		return None
	
	# Group data by date for trend chart
	dates = sorted(set([d.get("date") for d in data if d.get("date")]))
	
	carbon_data = []
	energy_data = []
	sustainability_scores = []
	
	for date in dates:
		date_data = [d for d in data if d.get("date") == date]
		total_carbon = sum(flt(d.get("carbon_footprint", 0)) for d in date_data)
		total_energy = sum(flt(d.get("energy_consumption", 0)) for d in date_data)
		avg_score = sum(flt(d.get("sustainability_score", 0)) for d in date_data) / len(date_data) if date_data else 0
		
		carbon_data.append({"name": str(date), "value": total_carbon})
		energy_data.append({"name": str(date), "value": total_energy})
		sustainability_scores.append({"name": str(date), "value": avg_score})
	
	chart = {
		"data": {
			"labels": [str(d) for d in dates],
			"datasets": [
				{
					"name": "Carbon Footprint (kg CO2e)",
					"values": [d["value"] for d in carbon_data]
				},
				{
					"name": "Energy Consumption (kWh)",
					"values": [d["value"] for d in energy_data]
				},
				{
					"name": "Sustainability Score",
					"values": [d["value"] for d in sustainability_scores]
				}
			]
		},
		"type": "line",
		"colors": ["#ff6384", "#36a2eb", "#4bc0c0"]
	}
	
	return chart

