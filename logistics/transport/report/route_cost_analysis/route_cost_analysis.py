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
			"fieldname": "route_name",
			"label": _("Route Name"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "from_location",
			"label": _("From Location"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "to_location",
			"label": _("To Location"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "total_trips",
			"label": _("Total Trips"),
			"fieldtype": "Int",
			"width": 100
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
			"fieldname": "avg_distance_per_trip",
			"label": _("Avg Distance/Trip (km)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 140
		},
		{
			"fieldname": "avg_duration_per_trip",
			"label": _("Avg Duration/Trip (hrs)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 140
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
			"fieldname": "cost_per_trip",
			"label": _("Cost per Trip"),
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
			"fieldname": "profit_margin",
			"label": _("Profit Margin %"),
			"fieldtype": "Percent",
			"precision": 2,
			"width": 120
		},
		{
			"fieldname": "efficiency_score",
			"label": _("Efficiency Score"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 120
		}
	]

def get_data(filters):
	conditions = get_conditions(filters)
	
	# Get route cost analysis data
	query = """
		SELECT 
			rs.route_name,
			rs.vehicle_type,
			rs.vehicle,
			rs.driver,
			rs.transport_company,
			COUNT(DISTINCT rs.name) as total_trips,
			SUM(COALESCE(tl.actual_distance_km, tl.distance_km, 0)) as total_distance,
			SUM(COALESCE(tl.actual_duration_min, tl.duration_min, 0)) / 60 as total_duration,
			AVG(COALESCE(tl.actual_distance_km, tl.distance_km, 0)) as avg_distance_per_trip,
			AVG(COALESCE(tl.actual_duration_min, tl.duration_min, 0)) / 60 as avg_duration_per_trip,
			SUM(COALESCE(tl.cargo_weight_kg, 0)) as total_cargo_weight,
			MAX(rs.run_date) as last_trip_date
		FROM `tabRun Sheet` rs
		LEFT JOIN `tabTransport Leg` tl ON tl.run_sheet = rs.name
		WHERE rs.docstatus = 1
		{conditions}
		GROUP BY rs.route_name, rs.vehicle_type, rs.vehicle, rs.driver, rs.transport_company
		ORDER BY total_distance DESC
	""".format(conditions=conditions)
	
	data = frappe.db.sql(query, as_dict=True)
	
	# Process data and calculate cost metrics
	for row in data:
		# Calculate cost components
		cost_metrics = calculate_route_costs(row)
		row.update(cost_metrics)
		
		# Calculate efficiency and profitability
		efficiency_metrics = calculate_efficiency_metrics(row)
		row.update(efficiency_metrics)
		
		# Get location information
		location_info = get_route_locations(row.route_name)
		row.update(location_info)
		
		# Format dates
		if row.last_trip_date:
			row.last_trip_date = getdate(row.last_trip_date)
	
	return data

def get_conditions(filters):
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("rs.run_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("rs.run_date <= %(to_date)s")
	
	if filters.get("route_name"):
		conditions.append("rs.route_name = %(route_name)s")
	
	if filters.get("vehicle_type"):
		conditions.append("rs.vehicle_type = %(vehicle_type)s")
	
	if filters.get("transport_company"):
		conditions.append("rs.transport_company = %(transport_company)s")
	
	if filters.get("cost_range"):
		# This would need to be implemented based on calculated costs
		pass
	
	return " AND ".join(conditions) if conditions else ""

def calculate_route_costs(row):
	"""Calculate various cost components for a route"""
	costs = {}
	
	# Fuel cost calculation
	fuel_cost = calculate_fuel_cost(row.total_distance, row.vehicle_type)
	costs["fuel_cost"] = fuel_cost
	
	# Driver cost calculation
	driver_cost = calculate_driver_cost(row.total_duration, row.driver)
	costs["driver_cost"] = driver_cost
	
	# Vehicle cost calculation
	vehicle_cost = calculate_vehicle_cost(row.total_distance, row.vehicle)
	costs["vehicle_cost"] = vehicle_cost
	
	# Maintenance cost calculation
	maintenance_cost = calculate_maintenance_cost(row.total_distance, row.vehicle_type)
	costs["maintenance_cost"] = maintenance_cost
	
	# Total cost
	total_cost = fuel_cost + driver_cost + vehicle_cost + maintenance_cost
	costs["total_cost"] = total_cost
	
	# Cost per kilometer
	if row.total_distance > 0:
		costs["cost_per_km"] = total_cost / row.total_distance
	else:
		costs["cost_per_km"] = 0
	
	# Cost per trip
	if row.total_trips > 0:
		costs["cost_per_trip"] = total_cost / row.total_trips
	else:
		costs["cost_per_trip"] = 0
	
	return costs

def calculate_fuel_cost(distance, vehicle_type):
	"""Calculate fuel cost based on distance and vehicle type"""
	# Fuel consumption rates (L/100km) by vehicle type
	fuel_consumption = {
		"Truck": 25,  # L/100km
		"Van": 12,
		"Car": 8,
		"Motorcycle": 4
	}
	
	consumption_rate = fuel_consumption.get(vehicle_type, 15)
	fuel_price_per_liter = 1.50  # USD per liter
	
	fuel_consumed = (distance / 100) * consumption_rate
	return fuel_consumed * fuel_price_per_liter

def calculate_driver_cost(duration, driver):
	"""Calculate driver cost based on duration"""
	# Default driver hourly rate
	hourly_rate = 25  # USD per hour
	
	# In a real implementation, this would get the actual driver rate
	# driver_doc = frappe.get_doc("Driver", driver)
	# hourly_rate = driver_doc.hourly_rate or 25
	
	return duration * hourly_rate

def calculate_vehicle_cost(distance, vehicle):
	"""Calculate vehicle cost based on distance"""
	# Default vehicle cost per km
	cost_per_km = 0.50  # USD per km
	
	# In a real implementation, this would get the actual vehicle cost
	# if vehicle:
	#     vehicle_doc = frappe.get_doc("Transport Vehicle", vehicle)
	#     cost_per_km = vehicle_doc.cost_per_km or 0.50
	
	return distance * cost_per_km

def calculate_maintenance_cost(distance, vehicle_type):
	"""Calculate maintenance cost based on distance and vehicle type"""
	# Maintenance cost per km by vehicle type
	maintenance_rates = {
		"Truck": 0.15,  # USD per km
		"Van": 0.08,
		"Car": 0.05,
		"Motorcycle": 0.03
	}
	
	rate = maintenance_rates.get(vehicle_type, 0.10)
	return distance * rate

def calculate_efficiency_metrics(row):
	"""Calculate efficiency and profitability metrics"""
	metrics = {}
	
	# Revenue calculation (simplified)
	# In a real implementation, this would come from actual revenue data
	revenue_per_km = 2.00  # USD per km
	revenue = row.total_distance * revenue_per_km
	metrics["revenue"] = revenue
	
	# Profit margin calculation
	if revenue > 0:
		profit_margin = ((revenue - row.total_cost) / revenue) * 100
		metrics["profit_margin"] = profit_margin
	else:
		metrics["profit_margin"] = 0
	
	# Efficiency score calculation
	efficiency_score = calculate_efficiency_score(row)
	metrics["efficiency_score"] = efficiency_score
	
	return metrics

def calculate_efficiency_score(row):
	"""Calculate overall efficiency score for a route"""
	score = 0
	
	# Distance efficiency (30% weight)
	if row.total_distance > 0:
		distance_score = min(row.total_distance / 100, 30)  # Max 30 points
		score += distance_score
	
	# Cost efficiency (40% weight)
	if row.cost_per_km > 0:
		cost_efficiency = max(0, 40 - (row.cost_per_km * 20))  # Lower cost per km = higher score
		score += cost_efficiency
	
	# Profitability (30% weight)
	if row.profit_margin > 0:
		profit_score = min(row.profit_margin * 0.3, 30)  # Max 30 points
		score += profit_score
	
	return min(score, 100)  # Cap at 100

def get_route_locations(route_name):
	"""Get from and to locations for a route"""
	# This is a simplified implementation
	# In a real implementation, this would parse the route name or get actual locations
	
	if not route_name:
		return {"from_location": "", "to_location": ""}
	
	# Simple parsing - in reality, this would be more sophisticated
	locations = route_name.split(" to ") if " to " in route_name else route_name.split(" - ")
	
	if len(locations) >= 2:
		return {
			"from_location": locations[0].strip(),
			"to_location": locations[1].strip()
		}
	else:
		return {
			"from_location": route_name,
			"to_location": "Unknown"
		}

def get_chart_data(data):
	"""Generate chart data for the report"""
	if not data:
		return None
	
	# Route cost comparison chart
	routes = [row.route_name for row in data[:10]]  # Top 10 routes
	total_costs = [row.total_cost for row in data[:10]]
	
	chart = {
		"data": {
			"labels": routes,
			"datasets": [
				{
					"name": "Total Cost",
					"values": total_costs
				}
			]
		},
		"type": "bar",
		"colors": ["#dc3545"]
	}
	
	return chart

def get_summary(data, filters):
	"""Generate summary statistics"""
	if not data:
		return []
	
	total_routes = len(data)
	total_trips = sum(row.total_trips for row in data)
	total_distance = sum(row.total_distance for row in data)
	total_cost = sum(row.total_cost for row in data)
	total_revenue = sum(row.revenue for row in data)
	
	avg_cost_per_km = total_cost / total_distance if total_distance > 0 else 0
	avg_profit_margin = sum(row.profit_margin for row in data) / total_routes if total_routes > 0 else 0
	
	# Count routes by efficiency
	high_efficiency = len([row for row in data if row.efficiency_score > 80])
	medium_efficiency = len([row for row in data if 60 <= row.efficiency_score <= 80])
	low_efficiency = len([row for row in data if row.efficiency_score < 60])
	
	return [
		{
			"label": _("Total Routes"),
			"value": total_routes,
			"indicator": "blue"
		},
		{
			"label": _("Total Trips"),
			"value": total_trips,
			"indicator": "green"
		},
		{
			"label": _("Total Distance (km)"),
			"value": f"{total_distance:,.2f}",
			"indicator": "blue"
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
			"indicator": "red" if avg_cost_per_km > 1.0 else "green"
		},
		{
			"label": _("Average Profit Margin %"),
			"value": f"{avg_profit_margin:.2f}%",
			"indicator": "green" if avg_profit_margin > 20 else "red"
		},
		{
			"label": _("High Efficiency Routes"),
			"value": high_efficiency,
			"indicator": "green"
		},
		{
			"label": _("Low Efficiency Routes"),
			"value": low_efficiency,
			"indicator": "red"
		}
	]
