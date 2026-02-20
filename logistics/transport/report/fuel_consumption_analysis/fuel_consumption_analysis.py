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

# Default report json so report_view.js can JSON.parse it (avoids "undefined" is not valid JSON)
DEFAULT_REPORT_JSON = '{"filters": [], "order_by": "creation desc", "add_totals_row": 0, "page_length": 20}'


def onload(doc, method=None):
	"""Ensure Fuel Consumption Analysis Report has valid json when loaded so report_view.js does not get undefined."""
	if doc.get("name") != "Fuel Consumption Analysis":
		return
	if doc.get("json") in (None, "", "null"):
		doc.json = DEFAULT_REPORT_JSON


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
			"fieldname": "vehicle",
			"label": _("Vehicle"),
			"fieldtype": "Link",
			"options": "Transport Vehicle",
			"width": 120
		},
		{
			"fieldname": "vehicle_name",
			"label": _("Vehicle Name"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "vehicle_type",
			"label": _("Vehicle Type"),
			"fieldtype": "Link",
			"options": "Vehicle Type",
			"width": 120
		},
		{
			"fieldname": "transport_company",
			"label": _("Transport Company"),
			"fieldtype": "Link",
			"options": "Transport Company",
			"width": 150
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
			"fieldname": "estimated_fuel_consumption",
			"label": _("Estimated Fuel (L)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 120
		},
		{
			"fieldname": "fuel_efficiency",
			"label": _("Fuel Efficiency (km/L)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 130
		},
		{
			"fieldname": "fuel_cost_per_km",
			"label": _("Fuel Cost per KM"),
			"fieldtype": "Currency",
			"options": currency,
			"width": 120
		},
		{
			"fieldname": "total_fuel_cost",
			"label": _("Total Fuel Cost"),
			"fieldtype": "Currency",
			"options": currency,
			"width": 120
		},
		{
			"fieldname": "co2_emissions",
			"label": _("CO₂ Emissions (kg)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 120
		},
		{
			"fieldname": "emission_factor",
			"label": _("Emission Factor"),
			"fieldtype": "Float",
			"precision": 4,
			"width": 120
		},
		{
			"fieldname": "cargo_weight",
			"label": _("Total Cargo Weight (kg)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 140
		},
		{
			"fieldname": "fuel_efficiency_per_ton",
			"label": _("Efficiency per Ton (km/L)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 140
		},
		{
			"fieldname": "runs_count",
			"label": _("Number of Runs"),
			"fieldtype": "Int",
			"width": 120
		},
		{
			"fieldname": "avg_distance_per_run",
			"label": _("Avg Distance per Run (km)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 140
		}
	]

def get_data(filters):
	conditions = get_conditions(filters)
	conditions_clause = (" AND " + conditions) if conditions else ""

	# Get fuel consumption data
	query = """
		SELECT 
			rs.vehicle,
			rs.vehicle_type,
			rs.transport_company,
			SUM(COALESCE(tl.actual_distance_km, tl.distance_km, 0)) as total_distance,
			SUM(COALESCE(tl.actual_duration_min, tl.duration_min, 0)) / 60 as total_duration,
			SUM(COALESCE(tl.cargo_weight_kg, 0)) as cargo_weight,
			SUM(COALESCE(tl.co2e_kg, 0)) as co2_emissions,
			AVG(COALESCE(tl.emission_factor, 0)) as emission_factor,
			COUNT(DISTINCT rs.name) as runs_count
		FROM `tabRun Sheet` rs
		LEFT JOIN `tabTransport Leg` tl ON tl.run_sheet = rs.name
		WHERE rs.docstatus = 1
		{conditions_clause}
		GROUP BY rs.vehicle, rs.vehicle_type, rs.transport_company
		ORDER BY total_distance DESC
	""".format(conditions_clause=conditions_clause)
	
	data = frappe.db.sql(query, filters or {}, as_dict=True)
	
	# Process data and calculate fuel metrics
	for row in data:
		vehicle_details = get_vehicle_details(row.vehicle)
		row.update(vehicle_details)
		
		# Calculate fuel consumption metrics
		fuel_metrics = calculate_fuel_metrics(row)
		row.update(fuel_metrics)
		
		# Calculate averages
		if row.runs_count > 0:
			row.avg_distance_per_run = row.total_distance / row.runs_count
		else:
			row.avg_distance_per_run = 0
	
	return data

def get_conditions(filters):
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("rs.run_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("rs.run_date <= %(to_date)s")
	
	if filters.get("vehicle"):
		conditions.append("rs.vehicle = %(vehicle)s")
	
	if filters.get("vehicle_type"):
		conditions.append("rs.vehicle_type = %(vehicle_type)s")
	
	if filters.get("transport_company"):
		conditions.append("rs.transport_company = %(transport_company)s")
	
	if filters.get("fuel_efficiency_range"):
		# This would need to be implemented based on calculated efficiency
		pass
	
	return " AND ".join(conditions) if conditions else ""

def get_vehicle_details(vehicle):
	"""Get vehicle details and specifications"""
	if not vehicle:
		return {}
	
	vehicle_doc = frappe.get_doc("Transport Vehicle", vehicle)
	return {
		"vehicle_name": vehicle_doc.vehicle_name,
		"make": vehicle_doc.make,
		"model": vehicle_doc.model,
		"avg_speed": vehicle_doc.avg_speed or 50,  # Default average speed
		"fuel_capacity": get_fuel_capacity(vehicle_doc.vehicle_type),
		"fuel_type": get_fuel_type(vehicle_doc.vehicle_type)
	}

def get_fuel_capacity(vehicle_type):
	"""Get fuel capacity based on vehicle type"""
	# This would need to be implemented based on vehicle type specifications
	# For now, return default values
	capacity_map = {
		"Truck": 200,  # liters
		"Van": 80,
		"Car": 60,
		"Motorcycle": 15
	}
	return capacity_map.get(vehicle_type, 100)

def get_fuel_type(vehicle_type):
	"""Get fuel type based on vehicle type"""
	# This would need to be implemented based on vehicle specifications
	return "Diesel"  # Default for most commercial vehicles

def calculate_fuel_metrics(row):
	"""Calculate fuel consumption and efficiency metrics"""
	metrics = {}
	
	# Estimate fuel consumption based on distance and vehicle type
	estimated_fuel = estimate_fuel_consumption(row.total_distance, row.vehicle_type, row.cargo_weight)
	metrics["estimated_fuel_consumption"] = estimated_fuel
	
	# Calculate fuel efficiency
	if estimated_fuel > 0:
		metrics["fuel_efficiency"] = row.total_distance / estimated_fuel
	else:
		metrics["fuel_efficiency"] = 0
	
	# Calculate fuel costs (assuming average fuel price)
	# Get currency from company if available
	company = row.get("company")
	currency = get_default_currency(company) if company else "USD"
	fuel_price_per_liter = get_fuel_price(currency)
	metrics["fuel_cost_per_km"] = (estimated_fuel * fuel_price_per_liter) / row.total_distance if row.total_distance > 0 else 0
	metrics["total_fuel_cost"] = estimated_fuel * fuel_price_per_liter
	
	# Calculate efficiency per ton
	if row.cargo_weight > 0:
		metrics["fuel_efficiency_per_ton"] = (row.total_distance / estimated_fuel) * (row.cargo_weight / 1000) if estimated_fuel > 0 else 0
	else:
		metrics["fuel_efficiency_per_ton"] = 0
	
	return metrics

def estimate_fuel_consumption(distance, vehicle_type, cargo_weight):
	"""Estimate fuel consumption based on distance, vehicle type, and cargo weight"""
	# Base fuel consumption rates (L/100km) by vehicle type
	base_consumption = {
		"Truck": 25,  # L/100km
		"Van": 12,
		"Car": 8,
		"Motorcycle": 4
	}
	
	base_rate = base_consumption.get(vehicle_type, 15)
	
	# Adjust for cargo weight (heavier loads consume more fuel)
	weight_factor = 1 + (cargo_weight / 10000)  # 10% increase per 1000kg
	
	# Calculate total consumption
	consumption_per_100km = base_rate * weight_factor
	total_consumption = (distance / 100) * consumption_per_100km
	
	return total_consumption

def get_fuel_price(currency="USD"):
	"""Get current fuel price per liter"""
	# This would need to be implemented based on actual fuel price data
	# For now, return a default price based on currency
	# Default prices in different currencies (simplified)
	fuel_prices = {
		"USD": 1.50,
		"EUR": 1.40,
		"GBP": 1.20,
		"PHP": 80.00,
		"INR": 120.00
	}
	return fuel_prices.get(currency, 1.50)

def get_chart_data(data):
	"""Generate chart data for the report"""
	if not data:
		return None
	
	# Fuel efficiency chart
	vehicles = [row.vehicle_name or row.vehicle for row in data[:10]]  # Top 10 vehicles
	fuel_efficiency = [row.fuel_efficiency for row in data[:10]]
	
	chart = {
		"data": {
			"labels": vehicles,
			"datasets": [
				{
					"name": "Fuel Efficiency (km/L)",
					"values": fuel_efficiency
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
	
	total_vehicles = len(data)
	total_distance = sum(row.total_distance for row in data)
	total_fuel = sum(row.estimated_fuel_consumption for row in data)
	total_cost = sum(row.total_fuel_cost for row in data)
	total_co2 = sum(row.co2_emissions for row in data)
	
	avg_efficiency = sum(row.fuel_efficiency for row in data) / total_vehicles if total_vehicles > 0 else 0
	avg_cost_per_km = total_cost / total_distance if total_distance > 0 else 0
	
	return [
		{
			"label": _("Total Vehicles"),
			"value": total_vehicles,
			"indicator": "blue"
		},
		{
			"label": _("Total Distance (km)"),
			"value": f"{total_distance:,.2f}",
			"indicator": "blue"
		},
		{
			"label": _("Total Fuel Consumption (L)"),
			"value": f"{total_fuel:,.2f}",
			"indicator": "orange"
		},
		{
			"label": _("Total Fuel Cost"),
			"value": fmt_money(total_cost, currency=currency),
			"indicator": "red"
		},
		{
			"label": _("Average Fuel Efficiency (km/L)"),
			"value": f"{avg_efficiency:.2f}",
			"indicator": "green" if avg_efficiency > 10 else "red"
		},
		{
			"label": _("Average Cost per KM"),
			"value": fmt_money(avg_cost_per_km, currency=currency),
			"indicator": "red" if avg_cost_per_km > 0.5 else "green"
		},
		{
			"label": _("Total CO₂ Emissions (kg)"),
			"value": f"{total_co2:,.2f}",
			"indicator": "red"
		},
		{
			"label": _("Fuel Cost per Liter"),
			"value": fmt_money(get_fuel_price(currency), currency=currency),
			"indicator": "blue"
		}
	]
