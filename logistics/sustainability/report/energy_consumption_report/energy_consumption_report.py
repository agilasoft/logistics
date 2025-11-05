# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_months


def execute(filters=None):
	"""Execute Energy Consumption Report"""
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
			"fieldname": "energy_type",
			"label": _("Energy Type"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "consumption_value",
			"label": _("Consumption Value"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 140
		},
		{
			"fieldname": "unit_of_measure",
			"label": _("Unit of Measure"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "total_cost",
			"label": _("Total Cost"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "carbon_footprint",
			"label": _("Carbon Footprint (kg CO2e)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 160
		},
		{
			"fieldname": "renewable_percentage",
			"label": _("Renewable Energy %"),
			"fieldtype": "Percent",
			"precision": 1,
			"width": 130
		},
		{
			"fieldname": "carbon_intensity",
			"label": _("Carbon Intensity (kg CO2e/unit)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 180
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
	if filters.energy_type:
		report_filters["energy_type"] = filters.energy_type
	
	# Handle date range filtering
	if filters.from_date and filters.to_date:
		report_filters["date"] = ["between", [filters.from_date, filters.to_date]]
	elif filters.from_date:
		report_filters["date"] = [">=", filters.from_date]
	elif filters.to_date:
		report_filters["date"] = ["<=", filters.to_date]
	
	# Get energy consumption data
	energy_data = frappe.get_all("Energy Consumption",
		filters=report_filters,
		fields=["name", "date", "module", "branch", "facility", "energy_type",
				"consumption_value", "unit_of_measure", "total_cost",
				"carbon_footprint", "renewable_percentage", "carbon_intensity"],
		order_by="date desc, module, branch"
	)
	
	# Format data for report
	data = []
	for record in energy_data:
		row = {
			"date": record.date,
			"module": record.module,
			"branch": record.branch,
			"facility": record.facility,
			"energy_type": record.energy_type,
			"consumption_value": flt(record.consumption_value),
			"unit_of_measure": record.unit_of_measure,
			"total_cost": flt(record.total_cost),
			"carbon_footprint": flt(record.carbon_footprint),
			"renewable_percentage": flt(record.renewable_percentage),
			"carbon_intensity": flt(record.carbon_intensity or 0)
		}
		data.append(row)
	
	return data


def get_chart_data(data):
	"""Generate chart data"""
	if not data:
		return None
	
	# Group by energy type for pie chart
	energy_type_data = {}
	for record in data:
		energy_type = record.get("energy_type") or "Unknown"
		if energy_type not in energy_type_data:
			energy_type_data[energy_type] = 0
		energy_type_data[energy_type] += flt(record.get("consumption_value", 0))
	
	# Group by date for line chart
	dates = sorted(set([d.get("date") for d in data if d.get("date")]))
	
	consumption_data = []
	renewable_data = []
	
	for date in dates:
		date_data = [d for d in data if d.get("date") == date]
		total_consumption = sum(flt(d.get("consumption_value", 0)) for d in date_data)
		avg_renewable = sum(flt(d.get("renewable_percentage", 0)) for d in date_data) / len(date_data) if date_data else 0
		
		consumption_data.append({"name": str(date), "value": total_consumption})
		renewable_data.append({"name": str(date), "value": avg_renewable})
	
	chart = {
		"data": {
			"labels": [str(d) for d in dates],
			"datasets": [
				{
					"name": "Energy Consumption",
					"values": [d["value"] for d in consumption_data]
				},
				{
					"name": "Renewable Energy %",
					"values": [d["value"] for d in renewable_data]
				}
			]
		},
		"type": "line",
		"colors": ["#36a2eb", "#4bc0c0"]
	}
	
	return chart

