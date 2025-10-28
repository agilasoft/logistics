# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_days, add_months
from frappe.model.document import Document
import json


@frappe.whitelist()
def get_sustainability_dashboard_data(site=None, facility=None, from_date=None, to_date=None):
	"""Get comprehensive sustainability dashboard data"""
	
	try:
		# Set default date range if not provided
		if not from_date:
			from_date = add_months(getdate(), -12)  # Last 12 months
		if not to_date:
			to_date = getdate()
		
		# Get energy consumption data
		energy_data = get_energy_consumption_data(site, facility, from_date, to_date)
		
		# Get carbon footprint data
		carbon_data = get_carbon_footprint_data(site, facility, from_date, to_date)
		
		# Get green operations metrics
		green_metrics = get_green_operations_metrics(site, facility, from_date, to_date)
		
		# Calculate sustainability scores
		sustainability_scores = calculate_sustainability_scores(energy_data, carbon_data, green_metrics)
		
		# Get trends and comparisons
		trends = get_sustainability_trends(site, facility, from_date, to_date)
		
		return {
			"energy_data": energy_data,
			"carbon_data": carbon_data,
			"green_metrics": green_metrics,
			"sustainability_scores": sustainability_scores,
			"trends": trends,
			"date_range": {
				"from_date": from_date,
				"to_date": to_date
			}
		}
		
	except Exception as e:
		frappe.log_error(f"Error in get_sustainability_dashboard_data: {str(e)}")
		# Return default data structure to prevent frontend errors
		return {
			"energy_data": {"summary": {"total_consumption": 0, "total_cost": 0, "average_renewable_percentage": 0, "carbon_intensity": 0}},
			"carbon_data": {"summary": {"total_emissions": 0, "average_daily_emissions": 0}},
			"green_metrics": {"green_score": 0, "renewable_percentage": 0},
			"sustainability_scores": {"overall_score": 0, "energy_score": 0, "carbon_score": 0, "green_score": 0},
			"trends": {"energy_improvement": 0, "carbon_improvement": 0},
			"date_range": {"from_date": from_date, "to_date": to_date}
		}


def get_energy_consumption_data(site=None, facility=None, from_date=None, to_date=None):
	"""Get energy consumption data for dashboard"""
	try:
		filters = {}
		if site:
			filters["site"] = site
		if facility:
			filters["facility"] = facility
		if from_date:
			filters["date"] = [">=", from_date]
		if to_date:
			filters["date"] = ["<=", to_date]
		
		energy_data = frappe.get_all("Energy Consumption", 
			filters=filters,
			fields=["date", "energy_type", "consumption_value", "carbon_footprint", 
					"renewable_percentage", "total_cost"],
			order_by="date desc"
		)
		
		# Calculate summary metrics
		total_consumption = sum(flt(d.consumption_value) for d in energy_data)
		total_carbon = sum(flt(d.carbon_footprint) for d in energy_data)
		total_cost = sum(flt(d.total_cost) for d in energy_data)
		
		# Calculate renewable energy percentage
		renewable_energy = sum(flt(d.renewable_percentage or 0) * flt(d.consumption_value) for d in energy_data)
		avg_renewable_pct = (renewable_energy / total_consumption * 100) if total_consumption > 0 else 0
		
		# Energy type breakdown
		energy_breakdown = {}
		for data in energy_data:
			energy_type = data.energy_type
			if energy_type not in energy_breakdown:
				energy_breakdown[energy_type] = 0
			energy_breakdown[energy_type] += flt(data.consumption_value)
		
		return {
			"energy_data": energy_data,
			"summary": {
				"total_consumption": total_consumption,
				"total_carbon_footprint": total_carbon,
				"total_cost": total_cost,
				"average_renewable_percentage": avg_renewable_pct,
				"carbon_intensity": total_carbon / total_consumption if total_consumption > 0 else 0
			},
			"energy_breakdown": energy_breakdown
		}
		
	except Exception as e:
		frappe.log_error(f"Error getting energy consumption data: {str(e)}")
		return {
			"energy_data": [],
			"summary": {
				"total_consumption": 0,
				"total_carbon_footprint": 0,
				"total_cost": 0,
				"average_renewable_percentage": 0,
				"carbon_intensity": 0
			},
			"energy_breakdown": {}
		}


def get_carbon_footprint_data(site=None, facility=None, from_date=None, to_date=None):
	"""Get carbon footprint data for dashboard"""
	try:
		filters = {}
		if site:
			filters["site"] = site
		if facility:
			filters["facility"] = facility
		if from_date:
			filters["date"] = [">=", from_date]
		if to_date:
			filters["date"] = ["<=", to_date]
		
		carbon_data = frappe.get_all("Carbon Footprint", 
			filters=filters,
			fields=["date", "scope", "total_emissions", "verification_status"],
			order_by="date desc"
		)
		
		# Calculate summary metrics
		total_emissions = sum(flt(d.total_emissions) for d in carbon_data)
		
		# Scope breakdown
		scope_breakdown = {}
		for data in carbon_data:
			scope = data.scope
			if scope not in scope_breakdown:
				scope_breakdown[scope] = 0
			scope_breakdown[scope] += flt(data.total_emissions)
		
		# Verification status breakdown
		verification_breakdown = {}
		for data in carbon_data:
			status = data.verification_status or "Not Verified"
			if status not in verification_breakdown:
				verification_breakdown[status] = 0
			verification_breakdown[status] += flt(data.total_emissions)
		
		return {
			"carbon_data": carbon_data,
			"summary": {
				"total_emissions": total_emissions,
				"average_daily_emissions": total_emissions / len(carbon_data) if carbon_data else 0
			},
			"scope_breakdown": scope_breakdown,
			"verification_breakdown": verification_breakdown
		}
		
	except Exception as e:
		frappe.log_error(f"Error getting carbon footprint data: {str(e)}")
		return {
			"carbon_data": [],
			"summary": {
				"total_emissions": 0,
				"average_daily_emissions": 0
			},
			"scope_breakdown": {},
			"verification_breakdown": {}
		}


def get_green_operations_metrics(site=None, facility=None, from_date=None, to_date=None):
	"""Get green operations metrics"""
	
	# Calculate green operations score
	green_score = calculate_green_operations_score(site, facility)
	
	# Get waste reduction metrics (if available)
	waste_metrics = get_waste_reduction_metrics(site, facility, from_date, to_date)
	
	# Get water usage metrics (if available)
	water_metrics = get_water_usage_metrics(site, facility, from_date, to_date)
	
	# Get renewable energy percentage from energy consumption data
	renewable_percentage = get_renewable_energy_percentage(site, facility, from_date, to_date)
	
	return {
		"green_score": green_score,
		"waste_metrics": waste_metrics,
		"water_metrics": water_metrics,
		"renewable_percentage": renewable_percentage,
		"certifications": []  # Placeholder for future certifications
	}


def calculate_sustainability_scores(energy_data, carbon_data, green_metrics):
	"""Calculate overall sustainability scores"""
	
	# Energy efficiency score (0-100)
	energy_score = 0
	if energy_data["summary"]["carbon_intensity"] > 0:
		# Lower carbon intensity = higher score
		energy_score = max(0, 100 - (energy_data["summary"]["carbon_intensity"] * 10))
	
	# Carbon footprint score (0-100)
	carbon_score = 0
	if carbon_data["summary"]["total_emissions"] > 0:
		# Lower emissions = higher score
		carbon_score = max(0, 100 - (carbon_data["summary"]["total_emissions"] / 1000))
	
	# Green operations score
	green_score = green_metrics.get("green_score", 0)
	
	# Overall sustainability score (weighted average)
	overall_score = (energy_score * 0.4) + (carbon_score * 0.4) + (green_score * 0.2)
	
	return {
		"overall_score": overall_score,
		"energy_score": energy_score,
		"carbon_score": carbon_score,
		"green_score": green_score,
		"rating": get_sustainability_rating(overall_score)
	}


def get_sustainability_rating(score):
	"""Get sustainability rating based on score"""
	if score >= 90:
		return "Excellent"
	elif score >= 80:
		return "Very Good"
	elif score >= 70:
		return "Good"
	elif score >= 60:
		return "Fair"
	elif score >= 50:
		return "Poor"
	else:
		return "Very Poor"


def get_sustainability_trends(site=None, facility=None, from_date=None, to_date=None):
	"""Get sustainability trends over time"""
	
	# Get monthly energy consumption trends
	energy_trends = get_monthly_energy_trends(site, facility, from_date, to_date)
	
	# Get monthly carbon footprint trends
	carbon_trends = get_monthly_carbon_trends(site, facility, from_date, to_date)
	
	# Calculate improvement percentages
	energy_improvement = calculate_improvement_percentage(energy_trends)
	carbon_improvement = calculate_improvement_percentage(carbon_trends)
	
	return {
		"energy_trends": energy_trends,
		"carbon_trends": carbon_trends,
		"energy_improvement": energy_improvement,
		"carbon_improvement": carbon_improvement
	}


def get_monthly_energy_trends(site=None, facility=None, from_date=None, to_date=None):
	"""Get monthly energy consumption trends"""
	# This would typically involve complex SQL queries
	# For now, return a simplified structure
	return {
		"months": [],
		"consumption": [],
		"carbon_footprint": [],
		"renewable_percentage": []
	}


def get_monthly_carbon_trends(site=None, facility=None, from_date=None, to_date=None):
	"""Get monthly carbon footprint trends"""
	# This would typically involve complex SQL queries
	# For now, return a simplified structure
	return {
		"months": [],
		"total_emissions": [],
		"scope_1": [],
		"scope_2": [],
		"scope_3": []
	}


def calculate_improvement_percentage(trends):
	"""Calculate improvement percentage from trends"""
	# Simplified calculation
	return 0


def calculate_green_operations_score(site=None, facility=None):
	"""Calculate green operations score based on various factors"""
	# This would involve complex calculations based on:
	# - Renewable energy usage
	# - Energy efficiency measures
	# - Waste reduction
	# - Water conservation
	# - Green certifications
	
	# For now, return a placeholder score
	return 75


def get_waste_reduction_metrics(site=None, facility=None, from_date=None, to_date=None):
	"""Get waste reduction metrics"""
	# Placeholder for waste reduction metrics
	return {
		"waste_generated": 0,
		"waste_recycled": 0,
		"waste_reduction_percentage": 0
	}


def get_water_usage_metrics(site=None, facility=None, from_date=None, to_date=None):
	"""Get water usage metrics"""
	# Placeholder for water usage metrics
	return {
		"water_consumption": 0,
		"water_recycled": 0,
		"water_efficiency_score": 0
	}


def get_renewable_energy_percentage(site=None, facility=None, from_date=None, to_date=None):
	"""Get renewable energy percentage from energy consumption data"""
	try:
		filters = {}
		if site:
			filters["site"] = site
		if facility:
			filters["facility"] = facility
		if from_date:
			filters["date"] = [">=", from_date]
		if to_date:
			filters["date"] = ["<=", to_date]
		
		# Get energy consumption data with renewable percentage
		energy_data = frappe.get_all("Energy Consumption", 
			filters=filters,
			fields=["consumption_value", "renewable_percentage"],
			order_by="date desc"
		)
		
		if not energy_data:
			return 0
		
		# Calculate weighted average renewable percentage
		total_consumption = sum(flt(d.consumption_value) for d in energy_data)
		renewable_consumption = sum(flt(d.renewable_percentage or 0) * flt(d.consumption_value) for d in energy_data)
		
		return (renewable_consumption / total_consumption * 100) if total_consumption > 0 else 0
		
	except Exception as e:
		frappe.log_error(f"Error getting renewable energy percentage: {str(e)}")
		return 0


@frappe.whitelist()
def get_sustainability_report(site=None, facility=None, from_date=None, to_date=None):
	"""Generate comprehensive sustainability report"""
	
	dashboard_data = get_sustainability_dashboard_data(site, facility, from_date, to_date)
	
	# Add additional report-specific data
	report_data = {
		"dashboard_data": dashboard_data,
		"recommendations": get_sustainability_recommendations(dashboard_data),
		"benchmarks": get_sustainability_benchmarks(),
		"action_plan": get_sustainability_action_plan(dashboard_data)
	}
	
	return report_data


def get_sustainability_recommendations(dashboard_data):
	"""Get sustainability improvement recommendations"""
	recommendations = []
	
	scores = dashboard_data.get("sustainability_scores", {})
	
	if scores.get("energy_score", 0) < 70:
		recommendations.append({
			"category": "Energy Efficiency",
			"priority": "High",
			"recommendation": "Implement LED lighting and energy-efficient HVAC systems",
			"potential_savings": "20-30% energy reduction"
		})
	
	if scores.get("carbon_score", 0) < 70:
		recommendations.append({
			"category": "Carbon Reduction",
			"priority": "High",
			"recommendation": "Increase renewable energy usage and optimize transportation",
			"potential_savings": "15-25% carbon reduction"
		})
	
	if scores.get("green_score", 0) < 70:
		recommendations.append({
			"category": "Green Operations",
			"priority": "Medium",
			"recommendation": "Implement waste reduction programs and water conservation",
			"potential_savings": "10-15% operational improvement"
		})
	
	return recommendations


def get_sustainability_benchmarks():
	"""Get industry sustainability benchmarks"""
	return {
		"energy_intensity": {
			"industry_average": 0.5,  # kWh per unit
			"best_practice": 0.3,
			"unit": "kWh per unit"
		},
		"carbon_intensity": {
			"industry_average": 0.4,  # kg CO2 per kWh
			"best_practice": 0.2,
			"unit": "kg CO2 per kWh"
		},
		"renewable_energy": {
			"industry_average": 25,  # percentage
			"best_practice": 50,
			"unit": "percentage"
		}
	}


def get_sustainability_action_plan(dashboard_data):
	"""Get sustainability action plan based on current performance"""
	action_plan = []
	
	scores = dashboard_data.get("sustainability_scores", {})
	
	if scores.get("overall_score", 0) < 60:
		action_plan.extend([
			{
				"phase": "Immediate (0-3 months)",
				"actions": [
					"Conduct energy audit",
					"Implement basic energy efficiency measures",
					"Start renewable energy assessment"
				]
			},
			{
				"phase": "Short-term (3-6 months)",
				"actions": [
					"Install energy monitoring systems",
					"Implement waste reduction programs",
					"Begin carbon footprint tracking"
				]
			},
			{
				"phase": "Long-term (6-12 months)",
				"actions": [
					"Install renewable energy systems",
					"Implement advanced efficiency measures",
					"Obtain green certifications"
				]
			}
		])
	
	return action_plan
