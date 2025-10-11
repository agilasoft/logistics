# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_days, add_months
from frappe.model.document import Document
from typing import Dict, List, Any, Optional


@frappe.whitelist()
def get_energy_efficiency_metrics(site=None, facility=None, from_date=None, to_date=None):
	"""Get energy efficiency metrics for sustainability tracking"""
	
	filters = {}
	if site:
		filters["site"] = site
	if facility:
		filters["facility"] = facility
	if from_date:
		filters["date"] = [">=", from_date]
	if to_date:
		filters["date"] = ["<=", to_date]
	
	# Get energy consumption data
	energy_data = frappe.get_all("Energy Consumption", 
		filters=filters,
		fields=["date", "energy_type", "consumption_value", "carbon_footprint", 
				"renewable_percentage", "total_cost", "efficiency_metrics"],
		order_by="date desc"
	)
	
	# Calculate efficiency metrics
	metrics = {
		"total_consumption": sum(flt(d.consumption_value) for d in energy_data),
		"total_carbon": sum(flt(d.carbon_footprint) for d in energy_data),
		"total_cost": sum(flt(d.total_cost) for d in energy_data),
		"average_renewable": 0,
		"carbon_intensity": 0,
		"energy_efficiency_score": 0
	}
	
	if energy_data:
		# Calculate average renewable percentage
		renewable_energy = sum(flt(d.renewable_percentage or 0) * flt(d.consumption_value) for d in energy_data)
		metrics["average_renewable"] = (renewable_energy / metrics["total_consumption"] * 100) if metrics["total_consumption"] > 0 else 0
		
		# Calculate carbon intensity
		metrics["carbon_intensity"] = metrics["total_carbon"] / metrics["total_consumption"] if metrics["total_consumption"] > 0 else 0
		
		# Calculate energy efficiency score
		metrics["energy_efficiency_score"] = calculate_energy_efficiency_score(energy_data)
	
	return {
		"metrics": metrics,
		"energy_data": energy_data,
		"recommendations": get_energy_efficiency_recommendations(metrics)
	}


def calculate_energy_efficiency_score(energy_data):
	"""Calculate overall energy efficiency score"""
	if not energy_data:
		return 0
	
	base_score = 50
	
	# Factor in renewable energy percentage
	avg_renewable = sum(flt(d.renewable_percentage or 0) for d in energy_data) / len(energy_data)
	base_score += avg_renewable * 0.5
	
	# Factor in carbon intensity
	total_consumption = sum(flt(d.consumption_value) for d in energy_data)
	total_carbon = sum(flt(d.carbon_footprint) for d in energy_data)
	if total_consumption > 0:
		carbon_intensity = total_carbon / total_consumption
		if carbon_intensity < 0.3:
			base_score += 20
		elif carbon_intensity < 0.5:
			base_score += 10
	
	return min(base_score, 100)


def get_energy_efficiency_recommendations(metrics):
	"""Get energy efficiency improvement recommendations"""
	recommendations = []
	
	if metrics["average_renewable"] < 25:
		recommendations.append({
			"category": "Renewable Energy",
			"priority": "High",
			"recommendation": "Increase renewable energy usage to at least 25%",
			"potential_impact": "Reduce carbon footprint by 15-20%"
		})
	
	if metrics["carbon_intensity"] > 0.4:
		recommendations.append({
			"category": "Energy Efficiency",
			"priority": "High",
			"recommendation": "Implement energy efficiency measures to reduce carbon intensity",
			"potential_impact": "Reduce carbon intensity by 20-30%"
		})
	
	if metrics["energy_efficiency_score"] < 70:
		recommendations.append({
			"category": "Overall Efficiency",
			"priority": "Medium",
			"recommendation": "Conduct energy audit and implement efficiency improvements",
			"potential_impact": "Improve overall efficiency score by 15-25 points"
		})
	
	return recommendations


@frappe.whitelist()
def get_carbon_footprint_analysis(site=None, facility=None, from_date=None, to_date=None):
	"""Get comprehensive carbon footprint analysis"""
	
	filters = {}
	if site:
		filters["site"] = site
	if facility:
		filters["facility"] = facility
	if from_date:
		filters["date"] = [">=", from_date]
	if to_date:
		filters["date"] = ["<=", to_date]
	
	# Get carbon footprint data
	carbon_data = frappe.get_all("Carbon Footprint", 
		filters=filters,
		fields=["date", "scope", "total_emissions", "verification_status", "emission_breakdown"],
		order_by="date desc"
	)
	
	# Calculate analysis metrics
	analysis = {
		"total_emissions": sum(flt(d.total_emissions) for d in carbon_data),
		"scope_breakdown": {},
		"verification_breakdown": {},
		"average_daily_emissions": 0,
		"carbon_intensity_trend": "stable",
		"reduction_potential": 0
	}
	
	if carbon_data:
		# Calculate scope breakdown
		for data in carbon_data:
			scope = data.scope
			if scope not in analysis["scope_breakdown"]:
				analysis["scope_breakdown"][scope] = 0
			analysis["scope_breakdown"][scope] += flt(data.total_emissions)
		
		# Calculate verification breakdown
		for data in carbon_data:
			status = data.verification_status or "Not Verified"
			if status not in analysis["verification_breakdown"]:
				analysis["verification_breakdown"][status] = 0
			analysis["verification_breakdown"][status] += flt(data.total_emissions)
		
		# Calculate average daily emissions
		analysis["average_daily_emissions"] = analysis["total_emissions"] / len(carbon_data)
		
		# Calculate reduction potential
		analysis["reduction_potential"] = calculate_reduction_potential(carbon_data)
	
	return {
		"analysis": analysis,
		"carbon_data": carbon_data,
		"recommendations": get_carbon_reduction_recommendations(analysis)
	}


def calculate_reduction_potential(carbon_data):
	"""Calculate potential carbon reduction"""
	if not carbon_data:
		return 0
	
	# Calculate potential reductions from various sources
	renewable_potential = 0.15  # 15% reduction from renewable energy
	efficiency_potential = 0.20  # 20% reduction from efficiency measures
	offset_potential = 0.10      # 10% reduction from offset programs
	
	total_potential = renewable_potential + efficiency_potential + offset_potential
	total_emissions = sum(flt(d.total_emissions) for d in carbon_data)
	
	return total_emissions * total_potential


def get_carbon_reduction_recommendations(analysis):
	"""Get carbon reduction recommendations"""
	recommendations = []
	
	if analysis["total_emissions"] > 1000:  # High emissions
		recommendations.append({
			"category": "High Priority",
			"recommendation": "Implement immediate carbon reduction measures",
			"potential_reduction": f"{analysis['reduction_potential']:.0f} kg CO2e"
		})
	
	# Scope-specific recommendations
	if analysis["scope_breakdown"].get("Scope 1", 0) > analysis["scope_breakdown"].get("Scope 2", 0):
		recommendations.append({
			"category": "Scope 1 Emissions",
			"recommendation": "Focus on reducing direct emissions from owned sources",
			"potential_reduction": "20-30% reduction"
		})
	
	if analysis["scope_breakdown"].get("Scope 2", 0) > 0:
		recommendations.append({
			"category": "Scope 2 Emissions",
			"recommendation": "Switch to renewable energy sources",
			"potential_reduction": "40-60% reduction"
		})
	
	return recommendations


@frappe.whitelist()
def get_green_operations_metrics(site=None, facility=None, from_date=None, to_date=None):
	"""Get green operations metrics and KPIs"""
	
	# Get green certifications
	certifications = get_green_certifications(site, facility)
	
	# Get waste reduction metrics
	waste_metrics = get_waste_reduction_metrics(site, facility, from_date, to_date)
	
	# Get water conservation metrics
	water_metrics = get_water_conservation_metrics(site, facility, from_date, to_date)
	
	# Calculate overall green score
	green_score = calculate_green_operations_score(certifications, waste_metrics, water_metrics)
	
	return {
		"green_score": green_score,
		"certifications": certifications,
		"waste_metrics": waste_metrics,
		"water_metrics": water_metrics,
		"recommendations": get_green_operations_recommendations(green_score, certifications)
	}


def get_green_certifications(site=None, facility=None):
	"""Get green certifications for the site/facility"""
	filters = {}
	if site:
		filters["site"] = site
	if facility:
		filters["facility"] = facility
	
	# Get certifications from energy consumption records
	certifications = frappe.get_all("Energy Consumption", 
		filters=filters,
		fields=["green_certifications"],
		limit=1
	)
	
	if certifications and certifications[0].green_certifications:
		# Parse certifications (this would need to be implemented based on the actual structure)
		return certifications[0].green_certifications
	
	return []


def get_waste_reduction_metrics(site=None, facility=None, from_date=None, to_date=None):
	"""Get waste reduction metrics"""
	# This would integrate with waste management system
	# For now, return placeholder data
	return {
		"waste_generated": 0,
		"waste_recycled": 0,
		"waste_reduction_percentage": 0,
		"recycling_rate": 0
	}


def get_water_conservation_metrics(site=None, facility=None, from_date=None, to_date=None):
	"""Get water conservation metrics"""
	# This would integrate with water management system
	# For now, return placeholder data
	return {
		"water_consumption": 0,
		"water_recycled": 0,
		"water_efficiency_score": 0,
		"water_reduction_percentage": 0
	}


def calculate_green_operations_score(certifications, waste_metrics, water_metrics):
	"""Calculate overall green operations score"""
	base_score = 50
	
	# Factor in certifications
	if certifications:
		certification_score = len(certifications) * 10
		base_score += min(certification_score, 30)
	
	# Factor in waste reduction
	waste_score = waste_metrics.get("recycling_rate", 0) * 0.3
	base_score += min(waste_score, 20)
	
	# Factor in water conservation
	water_score = water_metrics.get("water_efficiency_score", 0) * 0.2
	base_score += min(water_score, 20)
	
	return min(base_score, 100)


def get_green_operations_recommendations(green_score, certifications):
	"""Get green operations improvement recommendations"""
	recommendations = []
	
	if green_score < 70:
		recommendations.append({
			"category": "Overall Green Operations",
			"priority": "High",
			"recommendation": "Implement comprehensive green operations program",
			"potential_impact": "Improve green score by 20-30 points"
		})
	
	if len(certifications) < 2:
		recommendations.append({
			"category": "Green Certifications",
			"priority": "Medium",
			"recommendation": "Obtain additional green certifications",
			"potential_impact": "Enhance credibility and compliance"
		})
	
	return recommendations


@frappe.whitelist()
def get_sustainability_benchmarks():
	"""Get industry sustainability benchmarks"""
	return {
		"energy_intensity": {
			"industry_average": 0.5,
			"best_practice": 0.3,
			"excellent": 0.2,
			"unit": "kWh per unit"
		},
		"carbon_intensity": {
			"industry_average": 0.4,
			"best_practice": 0.2,
			"excellent": 0.1,
			"unit": "kg CO2 per kWh"
		},
		"renewable_energy": {
			"industry_average": 25,
			"best_practice": 50,
			"excellent": 75,
			"unit": "percentage"
		},
		"waste_reduction": {
			"industry_average": 30,
			"best_practice": 50,
			"excellent": 70,
			"unit": "percentage"
		},
		"water_efficiency": {
			"industry_average": 60,
			"best_practice": 80,
			"excellent": 90,
			"unit": "efficiency score"
		}
	}


@frappe.whitelist()
def get_sustainability_action_plan(site=None, facility=None):
	"""Get sustainability action plan based on current performance"""
	
	# Get current performance data
	energy_metrics = get_energy_efficiency_metrics(site, facility)
	carbon_analysis = get_carbon_footprint_analysis(site, facility)
	green_metrics = get_green_operations_metrics(site, facility)
	
	# Get benchmarks
	benchmarks = get_sustainability_benchmarks()
	
	# Generate action plan
	action_plan = []
	
	# Energy efficiency actions
	if energy_metrics["metrics"]["energy_efficiency_score"] < 70:
		action_plan.extend([
			{
				"phase": "Immediate (0-3 months)",
				"category": "Energy Efficiency",
				"actions": [
					"Conduct comprehensive energy audit",
					"Install energy monitoring systems",
					"Implement LED lighting replacement program"
				]
			},
			{
				"phase": "Short-term (3-6 months)",
				"category": "Energy Efficiency",
				"actions": [
					"Upgrade HVAC systems for better efficiency",
					"Implement smart building controls",
					"Train staff on energy conservation practices"
				]
			}
		])
	
	# Carbon reduction actions
	if carbon_analysis["analysis"]["total_emissions"] > 1000:
		action_plan.extend([
			{
				"phase": "Immediate (0-3 months)",
				"category": "Carbon Reduction",
				"actions": [
					"Implement carbon footprint tracking",
					"Start renewable energy assessment",
					"Begin waste reduction programs"
				]
			},
			{
				"phase": "Long-term (6-12 months)",
				"category": "Carbon Reduction",
				"actions": [
					"Install renewable energy systems",
					"Implement carbon offset programs",
					"Obtain carbon neutrality certification"
				]
			}
		])
	
	# Green operations actions
	if green_metrics["green_score"] < 70:
		action_plan.extend([
			{
				"phase": "Medium-term (3-9 months)",
				"category": "Green Operations",
				"actions": [
					"Implement comprehensive waste management",
					"Start water conservation programs",
					"Obtain green building certifications"
				]
			}
		])
	
	return {
		"action_plan": action_plan,
		"current_performance": {
			"energy_score": energy_metrics["metrics"]["energy_efficiency_score"],
			"carbon_emissions": carbon_analysis["analysis"]["total_emissions"],
			"green_score": green_metrics["green_score"]
		},
		"benchmarks": benchmarks
	}
