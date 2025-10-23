# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, get_datetime, format_datetime, format_date
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
			"fieldname": "transport_job",
			"label": _("Transport Job"),
			"fieldtype": "Link",
			"options": "Transport Job",
			"width": 150
		},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150
		},
		{
			"fieldname": "booking_date",
			"label": _("Booking Date"),
			"fieldtype": "Date",
			"width": 120
		},
		{
			"fieldname": "vehicle_type",
			"label": _("Vehicle Type"),
			"fieldtype": "Link",
			"options": "Vehicle Type",
			"width": 120
		},
		{
			"fieldname": "load_type",
			"label": _("Load Type"),
			"fieldtype": "Link",
			"options": "Load Type",
			"width": 120
		},
		{
			"fieldname": "total_distance",
			"label": _("Total Distance (km)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 120
		},
		{
			"fieldname": "total_duration",
			"label": _("Total Duration (hrs)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 120
		},
		{
			"fieldname": "fuel_cost",
			"label": _("Fuel Cost"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "driver_cost",
			"label": _("Driver Cost"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "vehicle_cost",
			"label": _("Vehicle Cost"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "maintenance_cost",
			"label": _("Maintenance Cost"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "toll_cost",
			"label": _("Toll Cost"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "other_costs",
			"label": _("Other Costs"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "total_cost",
			"label": _("Total Cost"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "cost_per_km",
			"label": _("Cost per KM"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "revenue",
			"label": _("Revenue"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "profit_loss",
			"label": _("Profit/Loss"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "profit_margin",
			"label": _("Profit Margin %"),
			"fieldtype": "Percent",
			"precision": 2,
			"width": 120
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100
		}
	]

def get_data(filters):
	conditions = get_conditions(filters)
	
	# Get transport job data with GL Entry costs
	query = """
		SELECT 
			tj.name as transport_job,
			tj.customer,
			tj.booking_date,
			tj.vehicle_type,
			tj.load_type,
			tj.status,
			tj.job_costing_number,
			tj.company,
			tj.branch,
			SUM(COALESCE(tl.actual_distance_km, tl.distance_km, 0)) as total_distance,
			SUM(COALESCE(tl.actual_duration_min, tl.duration_min, 0)) / 60 as total_duration
		FROM `tabTransport Job` tj
		LEFT JOIN `tabTransport Job Legs` tjl ON tjl.parent = tj.name
		LEFT JOIN `tabTransport Leg` tl ON tl.name = tjl.transport_leg
		WHERE tj.docstatus = 1
		{conditions}
		GROUP BY tj.name, tj.customer, tj.booking_date, tj.vehicle_type, tj.load_type, tj.status, tj.job_costing_number, tj.company, tj.branch
		ORDER BY tj.booking_date DESC
	""".format(conditions=conditions)
	
	data = frappe.db.sql(query, as_dict=True)
	
	# Process data and calculate costs from GL Entry
	for row in data:
		# Get costs from GL Entry
		cost_data = get_gl_entry_costs(row.transport_job, row.job_costing_number, row.company)
		row.update(cost_data)
		
		# Calculate derived metrics
		derived_metrics = calculate_derived_metrics(row)
		row.update(derived_metrics)
		
		# Format dates
		if row.booking_date:
			row.booking_date = getdate(row.booking_date)
	
	return data

def get_conditions(filters):
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("tj.booking_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("tj.booking_date <= %(to_date)s")
	
	if filters.get("customer"):
		conditions.append("tj.customer = %(customer)s")
	
	if filters.get("vehicle_type"):
		conditions.append("tj.vehicle_type = %(vehicle_type)s")
	
	if filters.get("load_type"):
		conditions.append("tj.load_type = %(load_type)s")
	
	if filters.get("company"):
		conditions.append("tj.company = %(company)s")
	
	if filters.get("status"):
		conditions.append("tj.status = %(status)s")
	
	return " AND ".join(conditions) if conditions else ""

def get_gl_entry_costs(transport_job, job_costing_number, company):
	"""Get cost data from GL Entry for a transport job"""
	costs = {
		"fuel_cost": 0,
		"driver_cost": 0,
		"vehicle_cost": 0,
		"maintenance_cost": 0,
		"toll_cost": 0,
		"other_costs": 0,
		"total_cost": 0,
		"revenue": 0
	}
	
	if not job_costing_number:
		return costs
	
	# Get GL Entry data for the job costing number
	gl_conditions = [
		"gle.job_costing_number = %(job_costing_number)s",
		"gle.company = %(company)s",
		"gle.docstatus = 1"
	]
	
	# Add date filters if provided
	if filters.get("from_date"):
		gl_conditions.append("gle.posting_date >= %(from_date)s")
	
	if filters.get("to_date"):
		gl_conditions.append("gle.posting_date <= %(to_date)s")
	
	gl_where = " AND ".join(gl_conditions)
	
	# Get cost breakdown from GL Entry
	cost_query = """
		SELECT 
			gle.account,
			SUM(gle.debit) as total_debit,
			SUM(gle.credit) as total_credit,
			SUM(gle.debit - gle.credit) as net_amount
		FROM `tabGL Entry` gle
		WHERE {gl_where}
		GROUP BY gle.account
	""".format(gl_where=gl_where)
	
	gl_data = frappe.db.sql(cost_query, {
		"job_costing_number": job_costing_number,
		"company": company,
		"from_date": filters.get("from_date"),
		"to_date": filters.get("to_date")
	}, as_dict=True)
	
	# Categorize costs based on account types
	for entry in gl_data:
		account = entry.account.lower()
		amount = abs(entry.net_amount)
		
		if "fuel" in account or "petrol" in account or "diesel" in account:
			costs["fuel_cost"] += amount
		elif "driver" in account or "salary" in account or "wage" in account:
			costs["driver_cost"] += amount
		elif "vehicle" in account or "truck" in account or "van" in account:
			costs["vehicle_cost"] += amount
		elif "maintenance" in account or "repair" in account or "service" in account:
			costs["maintenance_cost"] += amount
		elif "toll" in account or "tollway" in account:
			costs["toll_cost"] += amount
		else:
			costs["other_costs"] += amount
	
	# Calculate total cost
	costs["total_cost"] = sum([
		costs["fuel_cost"],
		costs["driver_cost"],
		costs["vehicle_cost"],
		costs["maintenance_cost"],
		costs["toll_cost"],
		costs["other_costs"]
	])
	
	# Get revenue from GL Entry (credit entries)
	revenue_query = """
		SELECT SUM(gle.credit) as total_revenue
		FROM `tabGL Entry` gle
		WHERE {gl_where}
		AND gle.credit > 0
	""".format(gl_where=gl_where)
	
	revenue_data = frappe.db.sql(revenue_query, {
		"job_costing_number": job_costing_number,
		"company": company,
		"from_date": filters.get("from_date"),
		"to_date": filters.get("to_date")
	}, as_dict=True)
	
	if revenue_data and revenue_data[0]:
		costs["revenue"] = revenue_data[0].total_revenue or 0
	
	return costs

def calculate_derived_metrics(row):
	"""Calculate derived metrics for the transport job"""
	metrics = {}
	
	# Cost per kilometer
	if row.total_distance > 0:
		metrics["cost_per_km"] = row.total_cost / row.total_distance
	else:
		metrics["cost_per_km"] = 0
	
	# Profit/Loss calculation
	metrics["profit_loss"] = row.revenue - row.total_cost
	
	# Profit margin calculation
	if row.revenue > 0:
		metrics["profit_margin"] = (metrics["profit_loss"] / row.revenue) * 100
	else:
		metrics["profit_margin"] = 0
	
	return metrics

def get_chart_data(data):
	"""Generate chart data for the report"""
	if not data:
		return None
	
	# Cost breakdown pie chart
	cost_categories = ["Fuel", "Driver", "Vehicle", "Maintenance", "Toll", "Other"]
	cost_values = [
		sum(row.fuel_cost for row in data),
		sum(row.driver_cost for row in data),
		sum(row.vehicle_cost for row in data),
		sum(row.maintenance_cost for row in data),
		sum(row.toll_cost for row in data),
		sum(row.other_costs for row in data)
	]
	
	chart = {
		"data": {
			"labels": cost_categories,
			"datasets": [
				{
					"name": "Cost Breakdown",
					"values": cost_values
				}
			]
		},
		"type": "pie",
		"colors": ["#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4", "#feca57", "#ff9ff3"]
	}
	
	return chart

def get_summary(data, filters):
	"""Generate summary statistics"""
	if not data:
		return []
	
	total_jobs = len(data)
	total_distance = sum(row.total_distance for row in data)
	total_duration = sum(row.total_duration for row in data)
	
	total_fuel_cost = sum(row.fuel_cost for row in data)
	total_driver_cost = sum(row.driver_cost for row in data)
	total_vehicle_cost = sum(row.vehicle_cost for row in data)
	total_maintenance_cost = sum(row.maintenance_cost for row in data)
	total_toll_cost = sum(row.toll_cost for row in data)
	total_other_costs = sum(row.other_costs for row in data)
	total_cost = sum(row.total_cost for row in data)
	total_revenue = sum(row.revenue for row in data)
	
	avg_cost_per_km = total_cost / total_distance if total_distance > 0 else 0
	avg_profit_margin = sum(row.profit_margin for row in data) / total_jobs if total_jobs > 0 else 0
	
	# Count jobs by profitability
	profitable_jobs = len([row for row in data if row.profit_loss > 0])
	loss_making_jobs = len([row for row in data if row.profit_loss < 0])
	
	return [
		{
			"label": _("Total Jobs"),
			"value": total_jobs,
			"indicator": "blue"
		},
		{
			"label": _("Total Distance (km)"),
			"value": f"{total_distance:,.2f}",
			"indicator": "blue"
		},
		{
			"label": _("Total Duration (hrs)"),
			"value": f"{total_duration:,.2f}",
			"indicator": "orange"
		},
		{
			"label": _("Total Fuel Cost"),
			"value": f"${total_fuel_cost:,.2f}",
			"indicator": "red"
		},
		{
			"label": _("Total Driver Cost"),
			"value": f"${total_driver_cost:,.2f}",
			"indicator": "red"
		},
		{
			"label": _("Total Vehicle Cost"),
			"value": f"${total_vehicle_cost:,.2f}",
			"indicator": "red"
		},
		{
			"label": _("Total Maintenance Cost"),
			"value": f"${total_maintenance_cost:,.2f}",
			"indicator": "red"
		},
		{
			"label": _("Total Cost"),
			"value": f"${total_cost:,.2f}",
			"indicator": "red"
		},
		{
			"label": _("Total Revenue"),
			"value": f"${total_revenue:,.2f}",
			"indicator": "green"
		},
		{
			"label": _("Average Cost per KM"),
			"value": f"${avg_cost_per_km:.2f}",
			"indicator": "red" if avg_cost_per_km > 2.0 else "green"
		},
		{
			"label": _("Average Profit Margin %"),
			"value": f"{avg_profit_margin:.2f}%",
			"indicator": "green" if avg_profit_margin > 10 else "red"
		},
		{
			"label": _("Profitable Jobs"),
			"value": profitable_jobs,
			"indicator": "green"
		},
		{
			"label": _("Loss Making Jobs"),
			"value": loss_making_jobs,
			"indicator": "red"
		}
	]
