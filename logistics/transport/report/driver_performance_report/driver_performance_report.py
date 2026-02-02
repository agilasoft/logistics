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
			"fieldname": "driver",
			"label": _("Driver"),
			"fieldtype": "Link",
			"options": "Driver",
			"width": 120
		},
		{
			"fieldname": "driver_name",
			"label": _("Driver Name"),
			"fieldtype": "Data",
			"width": 150
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
			"fieldname": "on_time_deliveries",
			"label": _("On-Time Deliveries"),
			"fieldtype": "Int",
			"width": 120
		},
		{
			"fieldname": "late_deliveries",
			"label": _("Late Deliveries"),
			"fieldtype": "Int",
			"width": 120
		},
		{
			"fieldname": "on_time_percentage",
			"label": _("On-Time %"),
			"fieldtype": "Percent",
			"precision": 2,
			"width": 120
		},
		{
			"fieldname": "avg_speed",
			"label": _("Average Speed (km/h)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 130
		},
		{
			"fieldname": "fuel_efficiency",
			"label": _("Fuel Efficiency (km/L)"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 130
		},
		{
			"fieldname": "safety_score",
			"label": _("Safety Score"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 120
		},
		{
			"fieldname": "performance_rating",
			"label": _("Performance Rating"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "last_run_date",
			"label": _("Last Run Date"),
			"fieldtype": "Date",
			"width": 120
		}
	]

def get_data(filters):
	conditions = get_conditions(filters)
	
	# Get driver performance data
	query = """
		SELECT 
			rs.driver,
			rs.driver_name,
			rs.transport_company,
			COUNT(DISTINCT rs.name) as total_runs,
			SUM(COALESCE(tl.actual_distance_km, tl.distance_km, 0)) as total_distance,
			SUM(COALESCE(tl.actual_duration_min, tl.duration_min, 0)) / 60 as total_duration,
			MAX(rs.run_date) as last_run_date,
			AVG(COALESCE(tl.actual_distance_km, tl.distance_km, 0)) as avg_distance_per_run,
			AVG(COALESCE(tl.actual_duration_min, tl.duration_min, 0)) / 60 as avg_duration_per_run
		FROM `tabRun Sheet` rs
		LEFT JOIN `tabTransport Leg` tl ON tl.run_sheet = rs.name
		WHERE rs.docstatus = 1
		{conditions}
		GROUP BY rs.driver, rs.driver_name, rs.transport_company
		ORDER BY total_distance DESC
	""".format(conditions=" AND " + conditions if conditions else "")
	
	data = frappe.db.sql(query, as_dict=True)
	
	# Process data and calculate performance metrics
	for row in data:
		# Calculate on-time delivery metrics
		on_time_metrics = calculate_on_time_metrics(row.driver, filters)
		row.update(on_time_metrics)
		
		# Calculate performance metrics
		performance_metrics = calculate_performance_metrics(row)
		row.update(performance_metrics)
		
		# Calculate safety score
		row.safety_score = calculate_safety_score(row)
		
		# Determine performance rating
		row.performance_rating = determine_performance_rating(row)
		
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
	
	if filters.get("driver"):
		conditions.append("rs.driver = %(driver)s")
	
	if filters.get("transport_company"):
		conditions.append("rs.transport_company = %(transport_company)s")
	
	if filters.get("performance_rating"):
		# This would need to be implemented based on calculated ratings
		pass
	
	return " AND ".join(conditions) if conditions else ""

def calculate_on_time_metrics(driver, filters):
	"""Calculate on-time delivery metrics for a driver"""
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("tl.end_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("tl.end_date <= %(to_date)s")
	
	conditions.append("rs.driver = %(driver)s")
	conditions.append("rs.docstatus = 1")
	
	where_clause = " AND ".join(conditions) if conditions else ""
	
	# Get delivery performance data
	query = """
		SELECT 
			COUNT(CASE WHEN tl.end_date <= tl.drop_window_end THEN 1 END) as on_time_deliveries,
			COUNT(CASE WHEN tl.end_date > tl.drop_window_end THEN 1 END) as late_deliveries,
			COUNT(*) as total_deliveries
		FROM `tabRun Sheet` rs
		LEFT JOIN `tabTransport Leg` tl ON tl.run_sheet = rs.name
		WHERE {where_clause}
	""".format(where_clause=where_clause)
	
	result = frappe.db.sql(query, {"driver": driver, **filters}, as_dict=True)
	
	if result and result[0]:
		row = result[0]
		on_time_deliveries = row.on_time_deliveries or 0
		late_deliveries = row.late_deliveries or 0
		total_deliveries = row.total_deliveries or 0
		
		on_time_percentage = (on_time_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0
		
		return {
			"on_time_deliveries": on_time_deliveries,
			"late_deliveries": late_deliveries,
			"on_time_percentage": on_time_percentage
		}
	
	return {
		"on_time_deliveries": 0,
		"late_deliveries": 0,
		"on_time_percentage": 0
	}

def calculate_performance_metrics(row):
	"""Calculate performance metrics for a driver"""
	metrics = {}
	
	# Calculate average speed
	if row.total_duration > 0:
		metrics["avg_speed"] = row.total_distance / row.total_duration
	else:
		metrics["avg_speed"] = 0
	
	# Estimate fuel efficiency (simplified calculation)
	if row.total_distance > 0:
		# Assume average fuel consumption of 15 L/100km for trucks
		estimated_fuel = (row.total_distance / 100) * 15
		metrics["fuel_efficiency"] = row.total_distance / estimated_fuel if estimated_fuel > 0 else 0
	else:
		metrics["fuel_efficiency"] = 0
	
	return metrics

def calculate_safety_score(row):
	"""Calculate safety score for a driver"""
	# This is a simplified safety score calculation
	# In a real implementation, this would consider:
	# - Accident history
	# - Speeding violations
	# - Route compliance
	# - Vehicle maintenance issues
	
	base_score = 100
	
	# Penalize for late deliveries (safety concern)
	if row.late_deliveries > 0:
		penalty = min(row.late_deliveries * 2, 20)  # Max 20 point penalty
		base_score -= penalty
	
	# Reward for on-time deliveries
	if row.on_time_percentage > 90:
		base_score += 5
	
	# Penalize for excessive speed
	if row.avg_speed > 80:  # Assuming 80 km/h is excessive
		base_score -= 10
	
	return max(base_score, 0)  # Ensure score doesn't go below 0

def determine_performance_rating(row):
	"""Determine overall performance rating for a driver"""
	score = 0
	
	# On-time delivery performance (40% weight)
	if row.on_time_percentage >= 95:
		score += 40
	elif row.on_time_percentage >= 90:
		score += 30
	elif row.on_time_percentage >= 80:
		score += 20
	else:
		score += 10
	
	# Distance performance (20% weight)
	if row.total_distance >= 1000:  # High mileage
		score += 20
	elif row.total_distance >= 500:
		score += 15
	else:
		score += 10
	
	# Safety score (40% weight)
	safety_weight = (row.safety_score / 100) * 40
	score += safety_weight
	
	# Determine rating
	if score >= 90:
		return "Excellent"
	elif score >= 80:
		return "Good"
	elif score >= 70:
		return "Average"
	elif score >= 60:
		return "Below Average"
	else:
		return "Poor"

def get_chart_data(data):
	"""Generate chart data for the report"""
	if not data:
		return None
	
	# Driver performance chart
	drivers = [row.driver_name or row.driver for row in data[:10]]  # Top 10 drivers
	performance_scores = []
	
	for row in data[:10]:
		# Calculate a composite performance score
		score = (row.on_time_percentage * 0.4) + (row.safety_score * 0.3) + (min(row.total_distance / 100, 30) * 0.3)
		performance_scores.append(score)
	
	chart = {
		"data": {
			"labels": drivers,
			"datasets": [
				{
					"name": "Performance Score",
					"values": performance_scores
				}
			]
		},
		"type": "bar",
		"colors": ["#007bff"]
	}
	
	return chart

def get_summary(data, filters):
	"""Generate summary statistics"""
	if not data:
		return []
	
	total_drivers = len(data)
	total_runs = sum(row.total_runs for row in data)
	total_distance = sum(row.total_distance for row in data)
	total_duration = sum(row.total_duration for row in data)
	
	avg_on_time = sum(row.on_time_percentage for row in data) / total_drivers if total_drivers > 0 else 0
	avg_safety = sum(row.safety_score for row in data) / total_drivers if total_drivers > 0 else 0
	
	# Count drivers by performance rating
	excellent_drivers = len([row for row in data if row.performance_rating == "Excellent"])
	good_drivers = len([row for row in data if row.performance_rating == "Good"])
	poor_drivers = len([row for row in data if row.performance_rating == "Poor"])
	
	return [
		{
			"label": _("Total Drivers"),
			"value": total_drivers,
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
			"label": _("Average On-Time %"),
			"value": f"{avg_on_time:.2f}%",
			"indicator": "green" if avg_on_time > 90 else "red"
		},
		{
			"label": _("Average Safety Score"),
			"value": f"{avg_safety:.1f}/100",
			"indicator": "green" if avg_safety > 80 else "red"
		},
		{
			"label": _("Excellent Drivers"),
			"value": excellent_drivers,
			"indicator": "green"
		},
		{
			"label": _("Good Drivers"),
			"value": good_drivers,
			"indicator": "blue"
		},
		{
			"label": _("Poor Performers"),
			"value": poor_drivers,
			"indicator": "red"
		}
	]
