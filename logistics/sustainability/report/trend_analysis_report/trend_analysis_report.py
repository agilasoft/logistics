# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_months


def execute(filters=None):
	"""Execute Trend Analysis Report"""
	filters = frappe._dict(filters or {})
	
	# Set default filters
	if not filters.from_date:
		filters.from_date = add_months(getdate(), -12)
	if not filters.to_date:
		filters.to_date = getdate()
	if not filters.period:
		filters.period = "monthly"
	
	# Get data based on filters
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)
	
	return columns, data, None, chart


def get_columns():
	"""Define report columns"""
	return [
		{
			"fieldname": "period",
			"label": _("Period"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "period_start",
			"label": _("Period Start"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "period_end",
			"label": _("Period End"),
			"fieldtype": "Date",
			"width": 100
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
		from logistics.sustainability.api.data_aggregation import get_trend_analysis
		
		trend_data = get_trend_analysis(
			module=filters.module,
			site=filters.branch,  # Using branch as site replacement
			facility=filters.facility,
			from_date=filters.from_date,
			to_date=filters.to_date,
			period=filters.period
		)
		
		# Get aggregated data by period
		from logistics.sustainability.api.data_aggregation import aggregate_metrics_by_period
		
		aggregated = aggregate_metrics_by_period(
			module=filters.module,
			site=filters.branch,
			facility=filters.facility,
			from_date=filters.from_date,
			to_date=filters.to_date,
			period=filters.period
		)
		
		data = []
		for period_data in aggregated:
			row = {
				"period": period_data.get("period"),
				"period_start": period_data.get("period_start"),
				"period_end": period_data.get("period_end"),
				"record_count": period_data.get("record_count", 0),
				"total_energy_consumption": flt(period_data.get("total_energy_consumption", 0)),
				"total_carbon_footprint": flt(period_data.get("total_carbon_footprint", 0)),
				"total_waste_generated": flt(period_data.get("total_waste_generated", 0)),
				"average_sustainability_score": flt(period_data.get("average_sustainability_score", 0)),
				"average_renewable_percentage": flt(period_data.get("average_renewable_percentage", 0))
			}
			data.append(row)
		
		return data
	except Exception as e:
		frappe.log_error(f"Error in Trend Analysis Report: {e}", "Trend Analysis Report Error")
		return []


def get_chart_data(data):
	"""Generate chart data"""
	if not data:
		return None
	
	periods = [d.get("period") for d in data]
	carbon_values = [flt(d.get("total_carbon_footprint", 0)) for d in data]
	energy_values = [flt(d.get("total_energy_consumption", 0)) for d in data]
	score_values = [flt(d.get("average_sustainability_score", 0)) for d in data]
	
	chart = {
		"data": {
			"labels": periods,
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
		"type": "line",
		"colors": ["#ff6384", "#36a2eb", "#4bc0c0"]
	}
	
	return chart

