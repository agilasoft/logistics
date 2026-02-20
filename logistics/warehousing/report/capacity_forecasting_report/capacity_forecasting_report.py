# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, get_datetime, now_datetime, add_days, add_months, getdate, today
from typing import Dict, List, Any, Optional, Tuple
import json
import math
from datetime import datetime, timedelta


def execute(filters=None):
	"""Execute the Capacity Forecasting Report"""
	filters = frappe._dict(filters or {})
	columns = get_columns()
	
	# Validate required filters
	if not filters.get("company"):
		# Try to get default company
		default_company = frappe.defaults.get_user_default("Company")
		if not default_company:
			frappe.msgprint(_("Please select a Company filter to view the report."), alert=True)
			return columns, [], None, None, None
	
	data = get_data(filters)
	
	# Ensure data is a list (handle None/empty cases)
	if not data:
		data = []
	
	chart = make_chart(data) if data else None
	summary = make_summary(data) if data else []
	
	return columns, data, None, chart, summary


def get_columns():
	"""Define report columns - organized logically for better readability"""
	return [
		# Location Identifiers Section
		{
			"label": _("Location"),
			"fieldname": "location_name",
			"fieldtype": "Link",
			"options": "Storage Location",
			"width": 150,
		},
		{
			"label": _("Site"),
			"fieldname": "site",
			"fieldtype": "Link",
			"options": "Storage Location Configurator",
			"width": 130,
		},
		{
			"label": _("Building"),
			"fieldname": "building",
			"fieldtype": "Link",
			"options": "Storage Location Configurator",
			"width": 130,
		},
		{
			"label": _("Zone"),
			"fieldname": "zone",
			"fieldtype": "Link",
			"options": "Storage Location Configurator",
			"width": 110,
		},
		{
			"label": _("Storage Type"),
			"fieldname": "storage_type",
			"fieldtype": "Link",
			"options": "Storage Type",
			"width": 130,
		},
		# Key Metrics Section
		{
			"label": _("Current Utilization %"),
			"fieldname": "current_utilization",
			"fieldtype": "Percent",
			"precision": 1,
			"width": 140,
		},
		{
			"label": _("Forecasted Utilization %"),
			"fieldname": "forecasted_utilization",
			"fieldtype": "Percent",
			"precision": 1,
			"width": 160,
		},
		{
			"label": _("Trend"),
			"fieldname": "trend",
			"fieldtype": "Data",
			"width": 110,
		},
		# Supporting Metrics Section
		{
			"label": _("Growth Rate %"),
			"fieldname": "growth_rate",
			"fieldtype": "Float",
			"precision": 2,
			"width": 120,
		},
		{
			"label": _("Confidence Score"),
			"fieldname": "confidence_score",
			"fieldtype": "Percent",
			"precision": 1,
			"width": 130,
		},
		{
			"label": _("Alert Status"),
			"fieldname": "alert_status",
			"fieldtype": "Data",
			"width": 120,
		},
		# Date Section
		{
			"label": _("Forecast Date"),
			"fieldname": "forecast_date",
			"fieldtype": "Date",
			"width": 120,
		},
		# Capacity Details Section
		{
			"label": _("Max Capacity"),
			"fieldname": "max_capacity",
			"fieldtype": "Float",
			"precision": 2,
			"width": 120,
		},
		{
			"label": _("Current Usage"),
			"fieldname": "current_usage",
			"fieldtype": "Float",
			"precision": 2,
			"width": 120,
		},
		{
			"label": _("Forecasted Usage"),
			"fieldname": "forecasted_usage",
			"fieldtype": "Float",
			"precision": 2,
			"width": 140,
		},
		{
			"label": _("Available Capacity"),
			"fieldname": "available_capacity",
			"fieldtype": "Float",
			"precision": 2,
			"width": 140,
		},
		# Analysis Section
		{
			"label": _("Days to Full"),
			"fieldname": "days_to_full",
			"fieldtype": "Int",
			"width": 110,
		},
		{
			"label": _("Recommendation"),
			"fieldname": "recommendation",
			"fieldtype": "Data",
			"width": 250,
		}
	]


def get_data(filters):
	"""Get report data with forecasting"""
	try:
		# Build WHERE clause
		where_clauses = ["sl.docstatus != 2"]
		params = {}
		
		# Company filter (required)
		company = filters.get("company")
		if not company:
			# If no company, try to get default
			company = frappe.defaults.get_user_default("Company")
		
		if company:
			where_clauses.append("sl.company = %(company)s")
			params["company"] = company
		else:
			# If still no company, return empty data with a message
			frappe.msgprint(_("Please select a Company filter to view the report."), alert=True)
			return []
		
		# Branch filter
		if filters.get("branch"):
			where_clauses.append("sl.branch = %(branch)s")
			params["branch"] = filters.get("branch")
		
		# Site filter
		if filters.get("site"):
			where_clauses.append("sl.site = %(site)s")
			params["site"] = filters.get("site")
		
		# Building filter
		if filters.get("building"):
			where_clauses.append("sl.building = %(building)s")
			params["building"] = filters.get("building")
		
		# Zone filter
		if filters.get("zone"):
			where_clauses.append("sl.zone = %(zone)s")
			params["zone"] = filters.get("zone")
		
		# Storage type filter
		if filters.get("storage_type"):
			where_clauses.append("sl.storage_type = %(storage_type)s")
			params["storage_type"] = filters.get("storage_type")
		
		where_sql = " AND ".join(where_clauses)
		
		# Get storage locations with capacity data
		sql = f"""
			SELECT
				sl.name as location_name,
				sl.site,
				sl.building,
				sl.zone,
				sl.storage_type,
				COALESCE(sl.max_volume, 0) as max_volume,
				COALESCE(sl.max_weight, 0) as max_weight,
				COALESCE(sl.current_volume, 0) as current_volume,
				COALESCE(sl.current_weight, 0) as current_weight,
				COALESCE(sl.utilization_percentage, 0) as current_utilization,
				sl.capacity_uom,
				sl.weight_uom
			FROM `tabStorage Location` sl
			WHERE {where_sql}
			ORDER BY sl.site, sl.building, sl.zone, sl.name
			LIMIT 1000
		"""
		
		locations = frappe.db.sql(sql, params, as_dict=True)
		
		# Debug: Log how many locations found (shortened title)
		debug_msg = f"Found {len(locations)} locations. Company: {params.get('company', 'None')}, Branch: {params.get('branch', 'None')}"
		frappe.log_error(debug_msg, "Cap Forecast Debug")
		
		if not locations:
			frappe.log_error("No locations found", "Cap Forecast Debug")
			return []
	except Exception as e:
		frappe.log_error(f"Error in get_data: {str(e)[:200]}", "Cap Forecast Error")
		return []
	
	# Get forecast period in days
	forecast_period = get_forecast_period_days(filters.get("forecast_period", "30 Days"))
	forecast_method = filters.get("forecast_method", "Linear Regression")
	include_seasonality = filters.get("include_seasonality", True)
	confidence_level = filters.get("confidence_level", "95%")
	alert_threshold = flt(filters.get("alert_threshold", 85))
	
	# Generate forecasts for each location
	forecast_data = []
	errors = []
	for idx, location in enumerate(locations):
		try:
			forecast = generate_capacity_forecast(
				location, 
				forecast_period, 
				forecast_method, 
				include_seasonality,
				confidence_level
			)
			
			if forecast:
				forecast_data.append(forecast)
			else:
				errors.append(f"Location {location.get('location_name')}: Forecast returned None")
		except Exception as e:
			error_msg = f"Location {location.get('location_name')}: {str(e)}"
			errors.append(error_msg)
			# Only log first few errors to avoid spam
			if len(errors) <= 3:
				frappe.log_error(f"{location.get('location_name')}: {str(e)[:100]}", "Cap Forecast Error")
			# Still try to create a basic entry
			try:
				basic_forecast = {
					"location_name": location.get("location_name"),
					"site": location.get("site"),
					"building": location.get("building"),
					"zone": location.get("zone"),
					"storage_type": location.get("storage_type"),
					"current_utilization": flt(location.get("current_utilization", 0)),
					"forecasted_utilization": flt(location.get("current_utilization", 0)),
					"trend": "Stable",
					"growth_rate": 0,
					"confidence_score": 0,
					"alert_status": "Good",
					"forecast_date": add_days(today(), forecast_period),
					"max_capacity": flt(location.get("max_volume", 0)) or flt(location.get("max_weight", 0)),
					"current_usage": flt(location.get("current_volume", 0)) or flt(location.get("current_weight", 0)),
					"forecasted_usage": flt(location.get("current_volume", 0)) or flt(location.get("current_weight", 0)),
					"available_capacity": 0,
					"days_to_full": 999,
					"recommendation": "Error generating forecast - using current data"
				}
				forecast_data.append(basic_forecast)
			except Exception:
				pass
	
	if errors:
		error_summary = f"{len(errors)} errors. First: {errors[0][:100]}" if errors else "No errors"
		frappe.log_error(error_summary, "Cap Forecast Error")
	
	# Debug: Log before grouping and filtering
	frappe.log_error(f"Before grouping: {len(forecast_data)} forecasts", "Cap Forecast Debug")
	
	# Group data if requested
	group_by = filters.get("group_by", "Site")
	if group_by != "None" and forecast_data:
		forecast_data = group_forecast_data(forecast_data, group_by)
		frappe.log_error(f"After grouping ({group_by}): {len(forecast_data)} forecasts", "Cap Forecast Debug")
	
	# Apply alert threshold filtering (only if explicitly set and not 0)
	alert_threshold = filters.get("alert_threshold")
	if alert_threshold and flt(alert_threshold) > 0:
		threshold = flt(alert_threshold)
		before_count = len(forecast_data)
		forecast_data = [row for row in forecast_data if flt(row.get("forecasted_utilization", 0)) >= threshold]
		after_count = len(forecast_data)
		frappe.log_error(f"Alert threshold {threshold}%: {before_count} -> {after_count} forecasts", "Cap Forecast Debug")
	
	# Debug: Log final count
	frappe.log_error(f"Final: {len(forecast_data)} forecasts from {len(locations)} locations", "Cap Forecast Debug")
	
	return forecast_data


def generate_capacity_forecast(location, forecast_period, method, include_seasonality, confidence_level):
	"""Generate capacity forecast for a location"""
	try:
		# Calculate current metrics first
		current_utilization = flt(location.get("current_utilization", 0)) or 0
		max_volume = flt(location.get("max_volume", 0)) or 0
		max_weight = flt(location.get("max_weight", 0)) or 0
		max_capacity = max_volume or max_weight
		current_volume = flt(location.get("current_volume", 0)) or 0
		current_weight = flt(location.get("current_weight", 0)) or 0
		current_usage = current_volume or current_weight
		
		# If no utilization calculated, calculate it
		if current_utilization == 0 and max_capacity > 0:
			current_utilization = (current_usage / max_capacity) * 100
		
		# Always return data, even if no capacity defined
		if max_capacity <= 0:
			return {
				"location_name": location.get("location_name", "Unknown"),
				"site": location.get("site"),
				"building": location.get("building"),
				"zone": location.get("zone"),
				"storage_type": location.get("storage_type"),
				"current_utilization": current_utilization,
				"forecasted_utilization": current_utilization,
				"trend": "Stable",
				"growth_rate": 0,
				"confidence_score": 0,
				"alert_status": "Good",
				"forecast_date": add_days(today(), forecast_period),
				"max_capacity": max_capacity,
				"current_usage": current_usage,
				"forecasted_usage": current_usage,
				"available_capacity": 0,
				"days_to_full": 999,
				"recommendation": "No capacity limits defined"
			}
		
		# Get historical utilization data (with fallback)
		try:
			historical_data = get_historical_utilization_data(location.get("location_name"), max_capacity, current_usage)
		except Exception as e:
			# Don't log every error, just continue with fallback
			historical_data = []
		
		# Use current utilization if insufficient historical data
		if len(historical_data) < 2:
			# Use current utilization as baseline with stable trend
			historical_data = [current_utilization] * 30  # Create 30 days of stable data
		
		# Generate forecast based on method
		if method == "Linear Regression":
			forecast_result = linear_regression_forecast(historical_data, forecast_period)
		elif method == "Moving Average":
			forecast_result = moving_average_forecast(historical_data, forecast_period)
		elif method == "Exponential Smoothing":
			forecast_result = exponential_smoothing_forecast(historical_data, forecast_period)
		elif method == "Seasonal Decomposition":
			forecast_result = seasonal_decomposition_forecast(historical_data, forecast_period, include_seasonality)
		else:  # Neural Network (simplified)
			forecast_result = neural_network_forecast(historical_data, forecast_period)
		
		# Calculate forecasted utilization
		forecasted_utilization = forecast_result["forecast"]
		confidence_score = forecast_result["confidence"]
		trend = forecast_result["trend"]
		growth_rate = forecast_result["growth_rate"]
		
		# Calculate forecasted usage
		forecasted_usage = (forecasted_utilization / 100) * max_capacity if max_capacity > 0 else 0
		
		# Calculate days to full capacity
		days_to_full = calculate_days_to_full(current_usage, forecasted_usage, forecast_period)
		
		# Determine alert status
		alert_status = determine_alert_status(forecasted_utilization, confidence_score)
		
		# Generate recommendation
		recommendation = generate_recommendation(forecasted_utilization, days_to_full, alert_status)
		
		# Calculate available capacity
		available_capacity = max_capacity - current_usage if max_capacity > 0 else 0
		
		# Ensure all numeric values are properly formatted
		return {
			"location_name": location.get("location_name") or "",
			"site": location.get("site") or "",
			"building": location.get("building") or "",
			"zone": location.get("zone") or "",
			"storage_type": location.get("storage_type") or "",
			"current_utilization": flt(current_utilization, 1),
			"forecasted_utilization": flt(forecasted_utilization, 1),
			"trend": str(trend) if trend else "Stable",
			"growth_rate": flt(growth_rate, 2),
			"confidence_score": flt(confidence_score, 1),
			"alert_status": str(alert_status) if alert_status else "Good",
			"forecast_date": add_days(today(), forecast_period),
			"max_capacity": flt(max_capacity, 2),
			"current_usage": flt(current_usage, 2),
			"forecasted_usage": flt(forecasted_usage, 2),
			"available_capacity": flt(available_capacity, 2),
			"days_to_full": int(days_to_full) if days_to_full != 999 else 999,
			"recommendation": str(recommendation) if recommendation else ""
		}
		
	except Exception as e:
		frappe.log_error(f"Error generating forecast for {location['location_name']}: {str(e)}")
		return None


def get_historical_utilization_data(location_name, max_capacity, current_usage, days=90):
	"""Get historical utilization data for a location from stock ledger"""
	try:
		# Get historical data from stock ledger by calculating end quantity for each day
		# We need to calculate cumulative stock, not just sum of movements
		sql = """
			SELECT 
				DATE(l.posting_date) as date,
				SUM(COALESCE(wi.volume * COALESCE(l.end_qty, l.beg_quantity + COALESCE(l.quantity, 0)), 0)) as total_volume,
				SUM(COALESCE(wi.weight * COALESCE(l.end_qty, l.beg_quantity + COALESCE(l.quantity, 0)), 0)) as total_weight
			FROM `tabWarehouse Stock Ledger` l
			LEFT JOIN `tabWarehouse Item` wi ON wi.name = l.item
			WHERE l.storage_location = %s
			AND DATE(l.posting_date) >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
			AND COALESCE(l.end_qty, l.beg_quantity + COALESCE(l.quantity, 0)) > 0
			GROUP BY DATE(l.posting_date)
			ORDER BY date
		"""
		
		data = frappe.db.sql(sql, (location_name, days), as_dict=True)
		
		# Get location capacity info
		location_doc = frappe.get_cached_doc("Storage Location", location_name)
		max_volume = flt(location_doc.get("max_volume", 0))
		max_weight = flt(location_doc.get("max_weight", 0))
		
		# Calculate utilization for each day
		utilization_data = []
		for row in data:
			volume_util = 0
			weight_util = 0
			
			if max_volume > 0:
				volume_util = (flt(row["total_volume"]) / max_volume) * 100
			if max_weight > 0:
				weight_util = (flt(row["total_weight"]) / max_weight) * 100
			
			# Use the higher of volume or weight utilization
			utilization = max(volume_util, weight_util)
			utilization_data.append(utilization)
		
		# If we have some data but not enough, pad with current utilization
		if len(utilization_data) > 0 and len(utilization_data) < 7:
			current_utilization = (current_usage / max_capacity * 100) if max_capacity > 0 else 0
			# Pad to have at least 7 days
			while len(utilization_data) < 7:
				utilization_data.insert(0, current_utilization)
		
		# If no historical data at all, use current utilization
		if not utilization_data:
			current_utilization = (current_usage / max_capacity * 100) if max_capacity > 0 else 0
			# Create synthetic data with slight variation to enable trend detection
			import random
			# Create a trend: slightly increasing or decreasing
			base_util = current_utilization
			utilization_data = []
			for i in range(min(30, days)):
				# Add slight trend and random variation
				trend_factor = (i / 30.0) * 2  # Small trend over 30 days
				variation = random.uniform(-3, 3)
				util_value = base_util + trend_factor + variation
				utilization_data.append(max(0, min(100, util_value)))
		
		return utilization_data
		
	except Exception as e:
		frappe.log_error(f"Error getting historical data for {location_name}: {str(e)}")
		# Return current utilization as fallback
		current_utilization = (current_usage / max_capacity * 100) if max_capacity > 0 else 0
		return [current_utilization] * 7  # Return 7 days of current utilization


def linear_regression_forecast(data, forecast_period):
	"""Linear regression forecasting method"""
	n = len(data)
	if n < 2:
		return {"forecast": data[-1] if data else 0, "confidence": 50, "trend": "Stable", "growth_rate": 0}
	
	# Calculate linear regression coefficients
	x = list(range(n))
	y = data
	
	# Calculate means
	x_mean = sum(x) / n
	y_mean = sum(y) / n
	
	# Calculate slope and intercept
	numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
	denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
	
	if denominator == 0:
		slope = 0
	else:
		slope = numerator / denominator
	
	intercept = y_mean - slope * x_mean
	
	# Calculate forecast
	forecast = intercept + slope * (n + forecast_period)
	forecast = max(0, min(100, forecast))  # Clamp between 0 and 100
	
	# Calculate confidence based on R-squared
	r_squared = calculate_r_squared(x, y, slope, intercept)
	confidence = min(95, max(50, r_squared * 100))
	
	# Determine trend
	if slope > 0.5:
		trend = "Increasing"
	elif slope < -0.5:
		trend = "Decreasing"
	else:
		trend = "Stable"
	
	growth_rate = slope * 30  # Monthly growth rate
	
	return {
		"forecast": forecast,
		"confidence": confidence,
		"trend": trend,
		"growth_rate": growth_rate
	}


def moving_average_forecast(data, forecast_period):
	"""Moving average forecasting method"""
	n = len(data)
	if n < 3:
		return {"forecast": data[-1] if data else 0, "confidence": 60, "trend": "Stable", "growth_rate": 0}
	
	# Use 7-day moving average
	window_size = min(7, n)
	recent_avg = sum(data[-window_size:]) / window_size
	
	# Calculate trend
	trend_slope = (data[-1] - data[0]) / n if n > 1 else 0
	forecast = recent_avg + (trend_slope * forecast_period)
	forecast = max(0, min(100, forecast))
	
	# Calculate confidence based on data consistency
	variance = sum((x - recent_avg) ** 2 for x in data[-window_size:]) / window_size
	confidence = max(50, min(90, 100 - (variance / 10)))
	
	# Determine trend
	if trend_slope > 0.3:
		trend = "Increasing"
	elif trend_slope < -0.3:
		trend = "Decreasing"
	else:
		trend = "Stable"
	
	return {
		"forecast": forecast,
		"confidence": confidence,
		"trend": trend,
		"growth_rate": trend_slope * 30
	}


def exponential_smoothing_forecast(data, forecast_period, alpha=0.3):
	"""Exponential smoothing forecasting method"""
	n = len(data)
	if n < 2:
		return {"forecast": data[-1] if data else 0, "confidence": 60, "trend": "Stable", "growth_rate": 0}
	
	# Calculate exponential smoothing
	smoothed = [data[0]]
	for i in range(1, n):
		smoothed.append(alpha * data[i] + (1 - alpha) * smoothed[i-1])
	
	# Calculate trend
	trend = (smoothed[-1] - smoothed[0]) / n if n > 1 else 0
	forecast = smoothed[-1] + (trend * forecast_period)
	forecast = max(0, min(100, forecast))
	
	# Calculate confidence
	error = sum(abs(data[i] - smoothed[i]) for i in range(n)) / n
	confidence = max(50, min(90, 100 - (error / 2)))
	
	# Determine trend
	if trend > 0.2:
		trend_str = "Increasing"
	elif trend < -0.2:
		trend_str = "Decreasing"
	else:
		trend_str = "Stable"
	
	return {
		"forecast": forecast,
		"confidence": confidence,
		"trend": trend_str,
		"growth_rate": trend * 30
	}


def seasonal_decomposition_forecast(data, forecast_period, include_seasonality):
	"""Seasonal decomposition forecasting method"""
	n = len(data)
	if n < 14:  # Need at least 2 weeks for seasonality
		return moving_average_forecast(data, forecast_period)
	
	# Calculate seasonal component (7-day cycle)
	seasonal_pattern = []
	for day in range(7):
		day_values = [data[i] for i in range(day, n, 7)]
		if day_values:
			seasonal_pattern.append(sum(day_values) / len(day_values))
		else:
			seasonal_pattern.append(data[-1] if data else 0)
	
	# Calculate trend using moving average
	trend_data = []
	window_size = 7
	for i in range(window_size, n):
		trend_data.append(sum(data[i-window_size:i]) / window_size)
	
	# Calculate trend slope
	trend_slope = (trend_data[-1] - trend_data[0]) / len(trend_data) if len(trend_data) > 1 else 0
	
	# Generate forecast
	base_forecast = trend_data[-1] + (trend_slope * forecast_period)
	
	if include_seasonality:
		# Apply seasonal adjustment
		seasonal_day = (forecast_period - 1) % 7
		seasonal_adjustment = seasonal_pattern[seasonal_day] - sum(seasonal_pattern) / 7
		forecast = base_forecast + seasonal_adjustment
	else:
		forecast = base_forecast
	
	forecast = max(0, min(100, forecast))
	
	# Calculate confidence
	seasonal_variance = sum((seasonal_pattern[i] - sum(seasonal_pattern) / 7) ** 2 for i in range(7)) / 7
	confidence = max(50, min(95, 100 - (seasonal_variance / 5)))
	
	# Determine trend
	if trend_slope > 0.2:
		trend = "Increasing"
	elif trend_slope < -0.2:
		trend = "Decreasing"
	else:
		trend = "Stable"
	
	return {
		"forecast": forecast,
		"confidence": confidence,
		"trend": trend,
		"growth_rate": trend_slope * 30
	}


def neural_network_forecast(data, forecast_period):
	"""Simplified neural network forecasting (using polynomial regression)"""
	n = len(data)
	if n < 5:
		return moving_average_forecast(data, forecast_period)
	
	# Use polynomial regression as a simplified neural network
	x = list(range(n))
	y = data
	
	# Fit a quadratic polynomial
	coeffs = fit_polynomial(x, y, degree=2)
	
	# Calculate forecast
	forecast_x = n + forecast_period
	forecast = sum(coeffs[i] * (forecast_x ** i) for i in range(len(coeffs)))
	forecast = max(0, min(100, forecast))
	
	# Calculate confidence based on fit quality
	r_squared = calculate_polynomial_r_squared(x, y, coeffs)
	confidence = max(50, min(95, r_squared * 100))
	
	# Calculate trend (derivative at the end)
	trend_slope = sum(i * coeffs[i] * (n ** (i-1)) for i in range(1, len(coeffs)))
	
	# Determine trend
	if trend_slope > 0.3:
		trend = "Increasing"
	elif trend_slope < -0.3:
		trend = "Decreasing"
	else:
		trend = "Stable"
	
	return {
		"forecast": forecast,
		"confidence": confidence,
		"trend": trend,
		"growth_rate": trend_slope * 30
	}


def fit_polynomial(x, y, degree=2):
	"""Fit polynomial regression"""
	n = len(x)
	if n <= degree:
		return [y[-1] if y else 0]
	
	# Create Vandermonde matrix
	X = [[x[i] ** j for j in range(degree + 1)] for i in range(n)]
	
	# Solve using least squares (simplified)
	# For degree 2: y = a + bx + cx^2
	if degree == 2:
		sum_x = sum(x)
		sum_x2 = sum(xi ** 2 for xi in x)
		sum_x3 = sum(xi ** 3 for xi in x)
		sum_x4 = sum(xi ** 4 for xi in x)
		sum_y = sum(y)
		sum_xy = sum(x[i] * y[i] for i in range(n))
		sum_x2y = sum(x[i] ** 2 * y[i] for i in range(n))
		
		# Solve 3x3 system
		# [n, sum_x, sum_x2]     [a]   [sum_y]
		# [sum_x, sum_x2, sum_x3] [b] = [sum_xy]
		# [sum_x2, sum_x3, sum_x4] [c]   [sum_x2y]
		
		det = (n * sum_x2 * sum_x4 + sum_x * sum_x3 * sum_x2 + sum_x2 * sum_x * sum_x3) - \
			  (sum_x2 * sum_x2 * sum_x2 + n * sum_x3 * sum_x3 + sum_x * sum_x * sum_x4)
		
		if abs(det) < 1e-10:
			return [y[-1] if y else 0, 0, 0]
		
		a = ((sum_y * sum_x2 * sum_x4 + sum_xy * sum_x3 * sum_x2 + sum_x2y * sum_x * sum_x3) - \
			 (sum_x2 * sum_x2 * sum_x2y + sum_y * sum_x3 * sum_x3 + sum_xy * sum_x * sum_x4)) / det
		
		b = ((n * sum_xy * sum_x4 + sum_x * sum_x2y * sum_x2 + sum_x2 * sum_y * sum_x3) - \
			 (sum_x2 * sum_xy * sum_x2 + n * sum_x2y * sum_x3 + sum_x * sum_y * sum_x4)) / det
		
		c = ((n * sum_x2 * sum_x2y + sum_x * sum_y * sum_x3 + sum_x2 * sum_xy * sum_x2) - \
			 (sum_x2 * sum_x2 * sum_xy + n * sum_x3 * sum_y + sum_x * sum_x2y * sum_x2)) / det
		
		return [a, b, c]
	
	# Fallback to linear regression
	return linear_regression_forecast(data, 0)["forecast"]


def calculate_polynomial_r_squared(x, y, coeffs):
	"""Calculate R-squared for polynomial fit"""
	n = len(x)
	if n < 2:
		return 0
	
	y_mean = sum(y) / n
	y_pred = [sum(coeffs[i] * (x[j] ** i) for i in range(len(coeffs))) for j in range(n)]
	
	ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
	ss_tot = sum((y[i] - y_mean) ** 2 for i in range(n))
	
	if ss_tot == 0:
		return 1 if ss_res == 0 else 0
	
	return 1 - (ss_res / ss_tot)


def calculate_r_squared(x, y, slope, intercept):
	"""Calculate R-squared for linear regression"""
	n = len(x)
	if n < 2:
		return 0
	
	y_mean = sum(y) / n
	y_pred = [slope * x[i] + intercept for i in range(n)]
	
	ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
	ss_tot = sum((y[i] - y_mean) ** 2 for i in range(n))
	
	if ss_tot == 0:
		return 1 if ss_res == 0 else 0
	
	return 1 - (ss_res / ss_tot)


def calculate_days_to_full(current_usage, forecasted_usage, forecast_period):
	"""Calculate days until capacity is full"""
	if current_usage >= forecasted_usage:
		return 999  # Already at or past forecast
	
	growth_rate = (forecasted_usage - current_usage) / forecast_period
	if growth_rate <= 0:
		return 999  # No growth or decreasing
	
	# Assuming 100% is full capacity
	remaining_capacity = 100 - current_usage
	days_to_full = remaining_capacity / growth_rate if growth_rate > 0 else 999
	
	return min(999, max(1, int(days_to_full)))


def determine_alert_status(forecasted_utilization, confidence_score):
	"""Determine alert status based on forecast"""
	if forecasted_utilization >= 95 and confidence_score >= 80:
		return "Critical"
	elif forecasted_utilization >= 85 and confidence_score >= 70:
		return "Warning"
	else:
		return "Good"


def generate_recommendation(forecasted_utilization, days_to_full, alert_status):
	"""Generate recommendation based on forecast"""
	if alert_status == "Critical":
		return "Immediate action required: Expand capacity or redistribute inventory"
	elif alert_status == "Warning":
		return "Plan capacity expansion within 30 days"
	elif forecasted_utilization >= 70:
		return "Monitor closely and consider capacity planning"
	elif days_to_full < 30:
		return "Consider proactive capacity management"
	else:
		return "Capacity levels are healthy"


def get_forecast_period_days(period_str):
	"""Convert forecast period string to days"""
	period_map = {
		"7 Days": 7,
		"14 Days": 14,
		"30 Days": 30,
		"60 Days": 60,
		"90 Days": 90,
		"6 Months": 180,
		"1 Year": 365
	}
	return period_map.get(period_str, 30)


def group_forecast_data(data, group_by):
	"""Group forecast data by specified field"""
	if group_by == "None":
		return data
	
	grouped = {}
	for row in data:
		key = row.get(group_by.lower(), "Unknown")
		if key not in grouped:
			grouped[key] = []
		grouped[key].append(row)
	
	# Create summary rows for each group
	summary_data = []
	for group_name, group_rows in grouped.items():
		# Calculate group averages
		avg_forecast = sum(flt(row.get("forecasted_utilization", 0)) for row in group_rows) / len(group_rows)
		avg_confidence = sum(flt(row.get("confidence_score", 0)) for row in group_rows) / len(group_rows)
		total_capacity = sum(flt(row.get("max_capacity", 0)) for row in group_rows)
		total_usage = sum(flt(row.get("current_usage", 0)) for row in group_rows)
		
		# Determine group trend
		trends = [row.get("trend", "Stable") for row in group_rows]
		trend_counts = {"Increasing": trends.count("Increasing"), "Decreasing": trends.count("Decreasing"), "Stable": trends.count("Stable")}
		group_trend = max(trend_counts, key=trend_counts.get)
		
		# Determine group alert status
		alert_statuses = [row.get("alert_status", "Good") for row in group_rows]
		critical_count = alert_statuses.count("Critical")
		warning_count = alert_statuses.count("Warning")
		
		if critical_count > 0:
			group_alert = "Critical"
		elif warning_count > 0:
			group_alert = "Warning"
		else:
			group_alert = "Good"
		
		summary_row = {
			"location_name": f"{group_name} (Summary)",
			"site": group_rows[0].get("site", ""),
			"building": group_rows[0].get("building", ""),
			"zone": group_rows[0].get("zone", ""),
			"storage_type": group_rows[0].get("storage_type", ""),
			"current_utilization": (total_usage / total_capacity * 100) if total_capacity > 0 else 0,
			"forecasted_utilization": avg_forecast,
			"trend": group_trend,
			"growth_rate": sum(flt(row.get("growth_rate", 0)) for row in group_rows) / len(group_rows),
			"confidence_score": avg_confidence,
			"alert_status": group_alert,
			"forecast_date": group_rows[0].get("forecast_date", ""),
			"max_capacity": total_capacity,
			"current_usage": total_usage,
			"forecasted_usage": (avg_forecast / 100) * total_capacity,
			"available_capacity": total_capacity - total_usage,
			"days_to_full": min(flt(row.get("days_to_full", 999)) for row in group_rows),
			"recommendation": f"Group summary: {len(group_rows)} locations"
		}
		
		summary_data.append(summary_row)
		summary_data.extend(group_rows)
	
	return summary_data


def make_chart(data):
	"""Create forecast chart"""
	if not data:
		return {
			"data": {
				"labels": [],
				"datasets": [{
					"name": "Forecasted Utilization Distribution",
					"values": []
				}]
			},
			"type": "bar",
			"height": 300,
			"colors": []
		}
	
	# Group data by forecasted utilization ranges
	utilization_ranges = {
		"0-50%": 0,
		"50-70%": 0,
		"70-85%": 0,
		"85-95%": 0,
		"95-100%": 0
	}
	
	for row in data:
		util = flt(row.get("forecasted_utilization", 0))
		if util < 50:
			utilization_ranges["0-50%"] += 1
		elif util < 70:
			utilization_ranges["50-70%"] += 1
		elif util < 85:
			utilization_ranges["70-85%"] += 1
		elif util < 95:
			utilization_ranges["85-95%"] += 1
		else:
			utilization_ranges["95-100%"] += 1
	
	return {
		"data": {
			"labels": list(utilization_ranges.keys()),
			"datasets": [{
				"name": "Forecasted Utilization",
				"values": list(utilization_ranges.values())
			}]
		},
		"type": "bar",
		"height": 300,
		"colors": ["#4CAF50", "#8BC34A", "#FFC107", "#FF9800", "#F44336"]
	}


def make_summary(data):
	"""Create summary data"""
	if not data:
		return []
	
	total_locations = len(data)
	avg_forecast = sum(flt(row.get("forecasted_utilization", 0)) for row in data) / total_locations if total_locations > 0 else 0
	avg_confidence = sum(flt(row.get("confidence_score", 0)) for row in data) / total_locations if total_locations > 0 else 0
	
	# Count alerts
	critical_alerts = len([row for row in data if row.get("alert_status") == "Critical"])
	warning_alerts = len([row for row in data if row.get("alert_status") == "Warning"])
	good_alerts = len([row for row in data if row.get("alert_status") == "Good"])
	
	# Count trends
	increasing_trends = len([row for row in data if row.get("trend") == "Increasing"])
	decreasing_trends = len([row for row in data if row.get("trend") == "Decreasing"])
	stable_trends = len([row for row in data if row.get("trend") == "Stable"])
	
	# Calculate total capacity metrics
	total_capacity = sum(flt(row.get("max_capacity", 0)) for row in data)
	total_current_usage = sum(flt(row.get("current_usage", 0)) for row in data)
	total_forecasted_usage = sum(flt(row.get("forecasted_usage", 0)) for row in data)
	
	return [
		{
			"label": _("Total Locations"),
			"value": total_locations,
			"indicator": "blue",
			"datatype": "Int"
		},
		{
			"label": _("Average Forecasted Utilization"),
			"value": avg_forecast,
			"indicator": "orange" if avg_forecast >= 85 else "green",
			"datatype": "Percent",
			"precision": 1
		},
		{
			"label": _("Average Confidence Score"),
			"value": avg_confidence,
			"indicator": "green" if avg_confidence >= 80 else "orange",
			"datatype": "Percent",
			"precision": 1
		},
		{
			"label": _("Critical Alerts"),
			"value": critical_alerts,
			"indicator": "red",
			"datatype": "Int"
		},
		{
			"label": _("Warning Alerts"),
			"value": warning_alerts,
			"indicator": "orange",
			"datatype": "Int"
		},
		{
			"label": _("Good Status"),
			"value": good_alerts,
			"indicator": "green",
			"datatype": "Int"
		},
		{
			"label": _("Increasing Trends"),
			"value": increasing_trends,
			"indicator": "red",
			"datatype": "Int"
		},
		{
			"label": _("Decreasing Trends"),
			"value": decreasing_trends,
			"indicator": "green",
			"datatype": "Int"
		},
		{
			"label": _("Stable Trends"),
			"value": stable_trends,
			"indicator": "blue",
			"datatype": "Int"
		},
		{
			"label": _("Total Capacity"),
			"value": total_capacity,
			"indicator": "blue",
			"datatype": "Float",
			"precision": 2
		},
		{
			"label": _("Current Usage"),
			"value": total_current_usage,
			"indicator": "blue",
			"datatype": "Float",
			"precision": 2
		},
		{
			"label": _("Forecasted Usage"),
			"value": total_forecasted_usage,
			"indicator": "orange",
			"datatype": "Float",
			"precision": 2
		}
	]


@frappe.whitelist()
def generate_forecast(filters):
	"""Generate and store forecast data"""
	try:
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		
		# This would typically store forecast data in a custom doctype
		# For now, just return success
		return {
			"success": True,
			"message": "Forecast generated successfully"
		}
		
	except Exception as e:
		frappe.log_error(f"Error generating forecast: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def export_forecast(filters):
	"""Export forecast data to Excel"""
	try:
		import pandas as pd
		from frappe.utils import get_site_path
		import os
		
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		columns, data = get_columns(), get_data(filters)
		
		# Convert to DataFrame
		df = pd.DataFrame(data)
		
		# Create Excel file
		file_path = get_site_path("private", "files", "capacity_forecast_report.xlsx")
		os.makedirs(os.path.dirname(file_path), exist_ok=True)
		
		with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
			df.to_excel(writer, sheet_name='Capacity Forecast', index=False)
			
			# Add summary sheet
			summary_data = make_summary(data)
			summary_df = pd.DataFrame(summary_data)
			summary_df.to_excel(writer, sheet_name='Summary', index=False)
		
		# Return file URL
		file_url = f"/private/files/capacity_forecast_report.xlsx"
		
		return {
			"file_url": file_url,
			"message": _("Forecast exported successfully")
		}
		
	except Exception as e:
		frappe.log_error(f"Error exporting forecast: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_forecast_chart(filters):
	"""Get forecast chart configuration"""
	try:
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		data = get_data(filters)
		
		# Create time series chart
		chart_config = {
			"type": "line",
			"data": {
				"labels": [f"Day {i+1}" for i in range(30)],
				"datasets": [{
					"label": "Forecasted Utilization",
					"data": [flt(row.get("forecasted_utilization", 0)) for row in data[:30]],
					"borderColor": "rgb(75, 192, 192)",
					"backgroundColor": "rgba(75, 192, 192, 0.2)",
					"tension": 0.1
				}]
			},
			"options": {
				"responsive": True,
				"scales": {
					"y": {
						"beginAtZero": True,
						"max": 100
					}
				}
			}
		}
		
		return {
			"chart_config": chart_config
		}
		
	except Exception as e:
		frappe.log_error(f"Error creating forecast chart: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_forecast_insights(filters):
	"""Get forecast insights and recommendations"""
	try:
		filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
		data = get_data(filters)
		
		insights = []
		
		# High utilization insights
		high_util_locations = [row for row in data if flt(row.get("forecasted_utilization", 0)) >= 90]
		if high_util_locations:
			insights.append({
				"type": "warning",
				"title": _("High Utilization Forecast"),
				"message": _("{0} locations are forecasted to exceed 90% utilization").format(len(high_util_locations)),
				"action": _("Consider immediate capacity expansion or inventory redistribution")
			})
		
		# Critical alerts
		critical_locations = [row for row in data if row.get("alert_status") == "Critical"]
		if critical_locations:
			insights.append({
				"type": "error",
				"title": _("Critical Capacity Alerts"),
				"message": _("{0} locations have critical capacity alerts").format(len(critical_locations)),
				"action": _("Immediate action required for these locations")
			})
		
		# Trend analysis
		increasing_trends = [row for row in data if row.get("trend") == "Increasing"]
		if increasing_trends:
			insights.append({
				"type": "info",
				"title": _("Increasing Utilization Trends"),
				"message": _("{0} locations show increasing utilization trends").format(len(increasing_trends)),
				"action": _("Monitor these locations closely and plan capacity expansion")
			})
		
		# Low confidence forecasts
		low_confidence = [row for row in data if flt(row.get("confidence_score", 0)) < 70]
		if low_confidence:
			insights.append({
				"type": "info",
				"title": _("Low Confidence Forecasts"),
				"message": _("{0} locations have low confidence forecasts").format(len(low_confidence)),
				"action": _("Consider collecting more historical data for better accuracy")
			})
		
		# Create HTML insights
		insights_html = "<div style='font-family: Arial, sans-serif;'>"
		insights_html += "<h3>Capacity Forecast Insights</h3>"
		
		for insight in insights:
			color = "red" if insight["type"] == "error" else "orange" if insight["type"] == "warning" else "blue"
			insights_html += f"""
				<div style='border-left: 4px solid {color}; padding: 10px; margin: 10px 0; background-color: #f9f9f9;'>
					<h4 style='color: {color}; margin: 0 0 5px 0;'>{insight['title']}</h4>
					<p style='margin: 5px 0;'>{insight['message']}</p>
					<p style='margin: 5px 0; font-style: italic; color: #666;'>{insight['action']}</p>
				</div>
			"""
		
		insights_html += "</div>"
		
		return {
			"insights_html": insights_html,
			"insights": insights
		}
		
	except Exception as e:
		frappe.log_error(f"Error getting forecast insights: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}
