# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, get_datetime, format_datetime, format_date, fmt_money
from datetime import datetime, timedelta

def get_default_currency(company=None):
	"""Get default currency for company or system default"""
	try:
		if company:
			currency = frappe.db.get_value("Company", company, "default_currency")
			if currency:
				return currency
		
		# Fallback to system default currency from Global Defaults
		currency = frappe.db.get_single_value("Global Defaults", "default_currency")
		if currency:
			return currency
			
		# Final fallback - get first company's currency
		first_company = frappe.db.get_value("Company", filters={"enabled": 1}, fieldname="name")
		if first_company:
			currency = frappe.db.get_value("Company", first_company, "default_currency")
			if currency:
				return currency
				
		# Ultimate fallback
		return "USD"
	except Exception:
		return "USD"

def get_currency_symbol(currency):
	"""Get currency symbol for a currency code"""
	try:
		currency_doc = frappe.get_doc("Currency", currency)
		return currency_doc.symbol or currency
	except Exception:
		return currency

def execute(filters=None):
	# Get currency for this report
	company = filters.get("company") if filters else None
	currency = get_default_currency(company)
	
	columns = get_columns(currency)
	data = get_data(filters)
	chart = get_chart_data(data)
	summary = get_summary(data, filters, currency)
	
	return columns, data, None, chart, summary

def get_columns(currency="USD"):
	return [
		{
			"fieldname": "consolidation",
			"label": _("Consolidation"),
			"fieldtype": "Link",
			"options": "Transport Consolidation",
			"width": 150
		},
		{
			"fieldname": "consolidation_date",
			"label": _("Consolidation Date"),
			"fieldtype": "Date",
			"width": 120
		},
		{
			"fieldname": "consolidation_type",
			"label": _("Consolidation Type"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "jobs_count",
			"label": _("Jobs Count"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "total_weight",
			"label": _("Total Weight (kg)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 120
		},
		{
			"fieldname": "total_volume",
			"label": _("Total Volume (m³)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 120
		},
		{
			"fieldname": "individual_cost",
			"label": _("Individual Cost"),
			"fieldtype": "Currency",
			"options": currency,
			"width": 120
		},
		{
			"fieldname": "consolidated_cost",
			"label": _("Consolidated Cost"),
			"fieldtype": "Currency",
			"options": currency,
			"width": 120
		},
		{
			"fieldname": "savings_amount",
			"label": _("Savings Amount"),
			"fieldtype": "Currency",
			"options": currency,
			"width": 120
		},
		{
			"fieldname": "savings_percentage",
			"label": _("Savings %"),
			"fieldtype": "Percent",
			"precision": 2,
			"width": 120
		},
		{
			"fieldname": "fuel_savings",
			"label": _("Fuel Savings"),
			"fieldtype": "Currency",
			"options": currency,
			"width": 120
		},
		{
			"fieldname": "driver_savings",
			"label": _("Driver Savings"),
			"fieldtype": "Currency",
			"options": currency,
			"width": 120
		},
		{
			"fieldname": "vehicle_savings",
			"label": _("Vehicle Savings"),
			"fieldtype": "Currency",
			"options": currency,
			"width": 120
		},
		{
			"fieldname": "efficiency_score",
			"label": _("Efficiency Score"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 120
		},
		{
			"fieldname": "run_sheet",
			"label": _("Run Sheet"),
			"fieldtype": "Link",
			"options": "Run Sheet",
			"width": 120
		}
	]

def get_data(filters):
	conditions = get_conditions(filters)
	
	# Get consolidation savings data
	query = """
		SELECT 
			tc.name as consolidation,
			tc.consolidation_date,
			tc.consolidation_type,
			tc.status,
			tc.total_weight,
			tc.total_volume,
			tc.run_sheet,
			tc.company,
			COUNT(tcj.transport_job) as jobs_count
		FROM `tabTransport Consolidation` tc
		LEFT JOIN `tabTransport Consolidation Job` tcj ON tcj.parent = tc.name
		WHERE tc.docstatus = 1
		{conditions}
		GROUP BY tc.name, tc.consolidation_date, tc.consolidation_type, tc.status, tc.total_weight, tc.total_volume, tc.run_sheet, tc.company
		ORDER BY tc.consolidation_date DESC
	""".format(conditions=" AND " + conditions if conditions else "")
	
	data = frappe.db.sql(query, filters, as_dict=True)
	
	# Process data and calculate savings metrics
	for row in data:
		# Calculate cost savings
		savings_metrics = calculate_consolidation_savings(row)
		row.update(savings_metrics)
		
		# Calculate efficiency score
		row.efficiency_score = calculate_efficiency_score(row)
		
		# Format dates
		if row.consolidation_date:
			row.consolidation_date = getdate(row.consolidation_date)
	
	return data

def get_conditions(filters):
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("tc.consolidation_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("tc.consolidation_date <= %(to_date)s")
	
	if filters.get("consolidation_type"):
		conditions.append("tc.consolidation_type = %(consolidation_type)s")
	
	if filters.get("status"):
		conditions.append("tc.status = %(status)s")
	
	if filters.get("run_sheet"):
		conditions.append("tc.run_sheet = %(run_sheet)s")
	
	if filters.get("company"):
		conditions.append("tc.company = %(company)s")
	
	return " AND ".join(conditions) if conditions else ""

def calculate_consolidation_savings(row):
	"""Calculate cost savings from consolidation"""
	savings = {}
	
	# Get individual job costs (simulated)
	individual_cost = calculate_individual_job_costs(row)
	savings["individual_cost"] = individual_cost
	
	# Get consolidated cost
	consolidated_cost = calculate_consolidated_cost(row)
	savings["consolidated_cost"] = consolidated_cost
	
	# Calculate total savings
	total_savings = individual_cost - consolidated_cost
	savings["savings_amount"] = total_savings
	
	# Calculate savings percentage
	if individual_cost > 0:
		savings["savings_percentage"] = (total_savings / individual_cost) * 100
	else:
		savings["savings_percentage"] = 0
	
	# Calculate savings breakdown
	savings_breakdown = calculate_savings_breakdown(row, total_savings)
	savings.update(savings_breakdown)
	
	return savings

def calculate_individual_job_costs(row):
	"""Calculate what it would cost to run jobs individually"""
	# Base cost per job
	base_cost_per_job = 150  # USD per job
	
	# Distance-based cost
	distance_cost = row.total_weight * 0.5  # $0.50 per kg
	
	# Time-based cost
	time_cost = row.jobs_count * 2  # $2 per job for time
	
	# Vehicle cost
	vehicle_cost = row.jobs_count * 100  # $100 per job for vehicle
	
	total_individual_cost = (row.jobs_count * base_cost_per_job) + distance_cost + time_cost + vehicle_cost
	
	return total_individual_cost

def calculate_consolidated_cost(row):
	"""Calculate the actual cost of consolidated transport"""
	# Base consolidation cost
	base_cost = 200  # USD base cost for consolidation
	
	# Distance-based cost (reduced due to efficiency)
	distance_cost = row.total_weight * 0.3  # $0.30 per kg (reduced)
	
	# Time-based cost (reduced due to single trip)
	time_cost = 5  # $5 for single trip
	
	# Vehicle cost (single vehicle)
	vehicle_cost = 120  # $120 for single vehicle
	
	# Efficiency bonus
	efficiency_bonus = 0.8  # 20% discount for consolidation
	
	total_consolidated_cost = (base_cost + distance_cost + time_cost + vehicle_cost) * efficiency_bonus
	
	return total_consolidated_cost

def calculate_savings_breakdown(row, total_savings):
	"""Calculate breakdown of savings by category"""
	# Distribute savings across categories
	fuel_savings = total_savings * 0.4  # 40% fuel savings
	driver_savings = total_savings * 0.3  # 30% driver savings
	vehicle_savings = total_savings * 0.3  # 30% vehicle savings
	
	return {
		"fuel_savings": fuel_savings,
		"driver_savings": driver_savings,
		"vehicle_savings": vehicle_savings
	}

def calculate_efficiency_score(row):
	"""Calculate efficiency score for consolidation"""
	score = 0
	
	# Jobs consolidation efficiency (40% weight)
	if row.jobs_count > 1:
		consolidation_efficiency = min(row.jobs_count * 10, 40)  # Max 40 points
		score += consolidation_efficiency
	
	# Weight efficiency (30% weight)
	if row.total_weight > 0:
		weight_efficiency = min(row.total_weight / 100, 30)  # Max 30 points
		score += weight_efficiency
	
	# Volume efficiency (30% weight)
	if row.total_volume > 0:
		volume_efficiency = min(row.total_volume * 10, 30)  # Max 30 points
		score += volume_efficiency
	
	return min(score, 100)  # Cap at 100

def get_chart_data(data):
	"""Generate chart data for the report"""
	if not data:
		return None
	
	# Consolidation savings chart
	consolidations = [row.consolidation for row in data[:10]]  # Top 10 consolidations
	savings_amounts = [row.savings_amount for row in data[:10]]
	
	chart = {
		"data": {
			"labels": consolidations,
			"datasets": [
				{
					"name": "Savings Amount",
					"values": savings_amounts
				}
			]
		},
		"type": "bar",
		"colors": ["#28a745"]
	}
	
	return chart

def get_summary(data, filters, currency="USD"):
	"""Generate summary statistics"""
	if not data:
		return []
	
	currency_symbol = get_currency_symbol(currency)
	
	total_consolidations = len(data)
	total_jobs = sum(row.jobs_count for row in data)
	total_weight = sum(row.total_weight for row in data)
	total_volume = sum(row.total_volume for row in data)
	
	total_individual_cost = sum(row.individual_cost for row in data)
	total_consolidated_cost = sum(row.consolidated_cost for row in data)
	total_savings = sum(row.savings_amount for row in data)
	
	avg_savings_percentage = sum(row.savings_percentage for row in data) / total_consolidations if total_consolidations > 0 else 0
	avg_efficiency = sum(row.efficiency_score for row in data) / total_consolidations if total_consolidations > 0 else 0
	
	# Count consolidations by efficiency
	high_efficiency = len([row for row in data if row.efficiency_score > 80])
	medium_efficiency = len([row for row in data if 60 <= row.efficiency_score <= 80])
	low_efficiency = len([row for row in data if row.efficiency_score < 60])
	
	return [
		{
			"label": _("Total Consolidations"),
			"value": total_consolidations,
			"indicator": "blue"
		},
		{
			"label": _("Total Jobs Consolidated"),
			"value": total_jobs,
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
			"indicator": "blue"
		},
		{
			"label": _("Total Individual Cost"),
			"value": fmt_money(total_individual_cost, currency=currency),
			"indicator": "red"
		},
		{
			"label": _("Total Consolidated Cost"),
			"value": fmt_money(total_consolidated_cost, currency=currency),
			"indicator": "orange"
		},
		{
			"label": _("Total Savings"),
			"value": fmt_money(total_savings, currency=currency),
			"indicator": "green"
		},
		{
			"label": _("Average Savings %"),
			"value": f"{avg_savings_percentage:.2f}%",
			"indicator": "green" if avg_savings_percentage > 20 else "red"
		},
		{
			"label": _("Average Efficiency Score"),
			"value": f"{avg_efficiency:.1f}/100",
			"indicator": "green" if avg_efficiency > 70 else "red"
		},
		{
			"label": _("High Efficiency Consolidations"),
			"value": high_efficiency,
			"indicator": "green"
		},
		{
			"label": _("Low Efficiency Consolidations"),
			"value": low_efficiency,
			"indicator": "red"
		}
	]
