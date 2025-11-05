# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_months


def execute(filters=None):
	"""Execute Carbon Footprint Report"""
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
			"fieldname": "scope",
			"label": _("Scope"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "total_emissions",
			"label": _("Total Emissions (kg CO2e)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 160
		},
		{
			"fieldname": "scope_1_emissions",
			"label": _("Scope 1 (kg CO2e)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 130
		},
		{
			"fieldname": "scope_2_emissions",
			"label": _("Scope 2 (kg CO2e)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 130
		},
		{
			"fieldname": "scope_3_emissions",
			"label": _("Scope 3 (kg CO2e)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 130
		},
		{
			"fieldname": "carbon_offset",
			"label": _("Carbon Offset (kg CO2e)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 150
		},
		{
			"fieldname": "net_emissions",
			"label": _("Net Emissions (kg CO2e)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 150
		},
		{
			"fieldname": "verification_status",
			"label": _("Verification Status"),
			"fieldtype": "Data",
			"width": 130
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
	if filters.scope:
		report_filters["scope"] = filters.scope
	
	# Handle date range filtering
	if filters.from_date and filters.to_date:
		report_filters["date"] = ["between", [filters.from_date, filters.to_date]]
	elif filters.from_date:
		report_filters["date"] = [">=", filters.from_date]
	elif filters.to_date:
		report_filters["date"] = ["<=", filters.to_date]
	
	# Get carbon footprint data
	carbon_data = frappe.get_all("Carbon Footprint",
		filters=report_filters,
		fields=["name", "date", "module", "branch", "facility", "scope",
				"total_emissions", "carbon_offset", "net_emissions", 
				"calculation_method", "verification_status"],
		order_by="date desc, module, branch"
	)
	
	# Format data for report and get emission breakdown from child table
	data = []
	for record in carbon_data:
		# Get emission breakdown data from child table
		breakdown_data = frappe.get_all(
			"Carbon Emission Breakdown",
			filters={"parent": record.name},
			fields=["scope", "emission_value"]
		)
		
		# Aggregate by scope
		scope_1 = 0
		scope_2 = 0
		scope_3 = 0
		for breakdown in breakdown_data:
			if breakdown.scope == "Scope 1":
				scope_1 = flt(breakdown.emission_value)
			elif breakdown.scope == "Scope 2":
				scope_2 = flt(breakdown.emission_value)
			elif breakdown.scope == "Scope 3":
				scope_3 = flt(breakdown.emission_value)
		
		row = {
			"date": record.date,
			"module": record.module,
			"branch": record.branch,
			"facility": record.facility,
			"scope": record.scope,
			"total_emissions": flt(record.total_emissions),
			"scope_1_emissions": scope_1,
			"scope_2_emissions": scope_2,
			"scope_3_emissions": scope_3,
			"carbon_offset": flt(record.carbon_offset),
			"net_emissions": flt(record.net_emissions),
			"calculation_method": record.calculation_method or "",
			"verification_status": record.verification_status
		}
		data.append(row)
	
	return data


def get_chart_data(data):
	"""Generate chart data"""
	if not data:
		return None
	
	# Group by scope for pie chart
	scope_data = {}
	for record in data:
		scope = record.get("scope") or "Total"
		if scope not in scope_data:
			scope_data[scope] = 0
		scope_data[scope] += flt(record.get("total_emissions", 0))
	
	# Group by date for line chart
	dates = sorted(set([d.get("date") for d in data if d.get("date")]))
	
	total_emissions = []
	net_emissions = []
	
	for date in dates:
		date_data = [d for d in data if d.get("date") == date]
		total = sum(flt(d.get("total_emissions", 0)) for d in date_data)
		net = sum(flt(d.get("net_emissions", 0)) for d in date_data)
		
		total_emissions.append({"name": str(date), "value": total})
		net_emissions.append({"name": str(date), "value": net})
	
	chart = {
		"data": {
			"labels": [str(d) for d in dates],
			"datasets": [
				{
					"name": "Total Emissions (kg CO2e)",
					"values": [d["value"] for d in total_emissions]
				},
				{
					"name": "Net Emissions (kg CO2e)",
					"values": [d["value"] for d in net_emissions]
				}
			]
		},
		"type": "line",
		"colors": ["#ff6384", "#36a2eb"]
	}
	
	return chart

