# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, get_datetime, format_datetime, format_date
from datetime import datetime, timedelta
import calendar

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)
	summary = get_summary(data, filters)
	
	return columns, data, None, chart, summary


def get_columns():
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
			"fieldname": "total_runs",
			"label": _("Total Runs"),
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
			"fieldname": "avg_distance_per_run",
			"label": _("Avg Distance/Run (km)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 130
		},
		{
			"fieldname": "avg_duration_per_run",
			"label": _("Avg Duration/Run (hrs)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 130
		},
		{
			"fieldname": "utilization_percentage",
			"label": _("Utilization %"),
			"fieldtype": "Percent",
			"precision": 2,
			"width": 120
		},
		{
			"fieldname": "fuel_efficiency",
			"label": _("Fuel Efficiency (km/l)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 130
		},
		{
			"fieldname": "cost_per_km",
			"label": _("Cost per KM"),
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
			"fieldname": "last_run_date",
			"label": _("Last Run Date"),
			"fieldtype": "Date",
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
	conditions_clause = (" AND " + conditions) if conditions else ""

	# Get vehicle utilization data
	query = """
		SELECT 
			rs.vehicle,
			rs.vehicle_type,
			rs.transport_company,
			COUNT(DISTINCT rs.name) as total_runs,
			SUM(COALESCE(tl.actual_distance_km, tl.distance_km, 0)) as total_distance,
			SUM(COALESCE(tl.actual_duration_min, tl.duration_min, 0)) / 60 as total_duration,
			AVG(COALESCE(tl.actual_distance_km, tl.distance_km, 0)) as avg_distance_per_run,
			AVG(COALESCE(tl.actual_duration_min, tl.duration_min, 0)) / 60 as avg_duration_per_run,
			MAX(rs.run_date) as last_run_date,
			rs.status
		FROM `tabRun Sheet` rs
		LEFT JOIN `tabTransport Leg` tl ON tl.run_sheet = rs.name
		WHERE rs.docstatus = 1
		{conditions_clause}
		GROUP BY rs.vehicle, rs.vehicle_type, rs.transport_company, rs.status
		ORDER BY total_distance DESC
	""".format(conditions_clause=conditions_clause)
	
	data = frappe.db.sql(query, as_dict=True)
	
	# Get vehicle details and calculate additional metrics
	for row in data:
		vehicle_details = get_vehicle_details(row.vehicle)
		row.update(vehicle_details)
		
		# Calculate utilization percentage
		row.utilization_percentage = calculate_utilization_percentage(row, filters)
		
		# Calculate cost metrics
		cost_metrics = calculate_cost_metrics(row, filters)
		row.update(cost_metrics)
		
		# Calculate fuel efficiency
		row.fuel_efficiency = calculate_fuel_efficiency(row)
		
		# Format dates
		if row.last_run_date:
			row.last_run_date = getdate(row.last_run_date)
	
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
	
	if filters.get("status"):
		conditions.append("rs.status = %(status)s")
	
	return " AND ".join(conditions) if conditions else ""

def get_vehicle_details(vehicle):
	if not vehicle:
		return {}
	
	vehicle_doc = frappe.get_doc("Transport Vehicle", vehicle)
	return {
		"vehicle_name": vehicle_doc.vehicle_name,
		"cost_per_km": vehicle_doc.cost_per_km or 0,
		"cost_per_hour": vehicle_doc.cost_per_hour or 0,
		"capacity_weight": vehicle_doc.capacity_weight or 0,
		"capacity_volume": vehicle_doc.capacity_volume or 0
	}

def calculate_utilization_percentage(row, filters):
	"""Calculate vehicle utilization percentage based on available time vs used time"""
	if not row.total_duration:
		return 0
	
	# Get the date range
	from_date = getdate(filters.get("from_date")) if filters.get("from_date") else getdate() - timedelta(days=30)
	to_date = getdate(filters.get("to_date")) if filters.get("to_date") else getdate()
	
	# Calculate total available hours in the period
	total_days = (to_date - from_date).days + 1
	total_available_hours = total_days * 24  # Assuming 24/7 availability
	
	if total_available_hours == 0:
		return 0
	
	utilization = (row.total_duration / total_available_hours) * 100
	return min(utilization, 100)  # Cap at 100%

def calculate_cost_metrics(row, filters):
	"""Calculate cost-related metrics"""
	total_cost = 0
	
	# Distance-based cost
	if row.cost_per_km and row.total_distance:
		total_cost += row.cost_per_km * row.total_distance
	
	# Time-based cost
	if row.cost_per_hour and row.total_duration:
		total_cost += row.cost_per_hour * row.total_duration
	
	return {
		"total_cost": total_cost,
		"cost_per_km": row.cost_per_km or 0
	}

def calculate_fuel_efficiency(row):
	"""Calculate fuel efficiency if fuel data is available"""
	# This would need to be implemented based on actual fuel tracking
	# For now, return a placeholder calculation
	if row.total_distance and row.total_distance > 0:
		# Assuming average fuel efficiency of 10 km/l (placeholder)
		return 10.0
	return 0

def get_chart_data(data):
	"""Generate chart data for the report"""
	if not data:
		return None
	
	# Vehicle utilization chart
	vehicles = [row.vehicle_name or row.vehicle for row in data[:10]]  # Top 10 vehicles
	utilization = [row.utilization_percentage for row in data[:10]]
	
	chart = {
		"data": {
			"labels": vehicles,
			"datasets": [
				{
					"name": "Utilization %",
					"values": utilization
				}
			]
		},
		"type": "bar",
		"colors": ["#5e64ff"]
	}
	
	return chart

def get_summary(data, filters):
	"""Generate summary statistics"""
	if not data:
		return []
	
	total_vehicles = len(data)
	total_runs = sum(row.total_runs for row in data)
	total_distance = sum(row.total_distance for row in data)
	total_duration = sum(row.total_duration for row in data)
	avg_utilization = sum(row.utilization_percentage for row in data) / total_vehicles if total_vehicles > 0 else 0
	
	return [
		{
			"label": _("Total Vehicles"),
			"value": total_vehicles,
			"indicator": "blue"
		},
		{
			"label": _("Total Runs"),
			"value": total_runs,
			"indicator": "green"
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
			"label": _("Average Utilization %"),
			"value": f"{avg_utilization:.2f}%",
			"indicator": "green" if avg_utilization > 70 else "red"
		}
	]
