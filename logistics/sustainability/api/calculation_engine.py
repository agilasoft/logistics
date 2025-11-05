# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate
from typing import Dict, List, Any, Optional
import math


class SustainabilityCalculationEngine:
	"""Centralized calculation engine for all sustainability metrics"""
	
	def __init__(self, company=None):
		self.company = company or frappe.defaults.get_user_default("Company")
		self.emission_factors = self._load_emission_factors()
	
	def _load_emission_factors(self):
		"""Load emission factors from database"""
		factors = frappe.get_all("Emission Factors",
			filters={"is_active": 1},
			fields=["*"]
		)
		
		# Organize factors by category and module
		organized_factors = {}
		for factor in factors:
			category = factor.category or "Other"
			module = factor.module or "All"
			
			if category not in organized_factors:
				organized_factors[category] = {}
			if module not in organized_factors[category]:
				organized_factors[category][module] = []
			
			organized_factors[category][module].append(factor)
		
		return organized_factors
	
	def calculate_carbon_footprint(self, activity_data, activity_type, module="All", date=None):
		"""Calculate carbon footprint for given activity data"""
		if not date:
			date = getdate()
		
		# Get relevant emission factors
		factors = self._get_emission_factors(activity_type, module, date)
		
		if not factors:
			frappe.throw(_(f"No emission factors found for {activity_type} in {module} module"))
		
		total_emissions = 0
		emission_breakdown = []
		
		for factor in factors:
			activity_value = flt(activity_data.get(factor.factor_name, 0))
			if activity_value <= 0:
				continue
			
			emission_value = activity_value * flt(factor.factor_value)
			total_emissions += emission_value
			
			emission_breakdown.append({
				"emission_source": factor.factor_name,
				"emission_value": emission_value,
				"unit_of_measure": factor.unit_of_measure,
				"emission_factor": factor.factor_value,
				"activity_data": activity_value,
				"scope": factor.scope,
				"source": factor.source
			})
		
		return {
			"total_emissions": total_emissions,
			"emission_breakdown": emission_breakdown,
			"calculation_method": "Emission Factor",
			"calculation_date": date
		}
	
	def calculate_energy_efficiency(self, energy_data, activity_data):
		"""Calculate energy efficiency metrics"""
		if not energy_data or not activity_data:
			return {}
		
		efficiency_metrics = {}
		
		# Basic energy metrics
		energy_consumption = flt(energy_data.get("consumption_value", 0))
		activity_value = flt(activity_data.get("activity_value", 0))
		
		if energy_consumption > 0 and activity_value > 0:
			# Energy intensity (energy per unit of activity)
			efficiency_metrics["energy_intensity"] = energy_consumption / activity_value
			
			# Energy efficiency score (lower intensity = higher score)
			efficiency_metrics["energy_efficiency_score"] = max(0, 100 - (efficiency_metrics["energy_intensity"] * 10))
		
		# Carbon intensity
		carbon_footprint = flt(energy_data.get("carbon_footprint", 0))
		if carbon_footprint > 0 and activity_value > 0:
			efficiency_metrics["carbon_intensity"] = carbon_footprint / activity_value
			efficiency_metrics["carbon_efficiency_score"] = max(0, 100 - (efficiency_metrics["carbon_intensity"] * 10))
		
		# Renewable energy impact
		renewable_percentage = flt(energy_data.get("renewable_percentage", 0))
		if renewable_percentage > 0:
			efficiency_metrics["renewable_energy_impact"] = self._calculate_renewable_impact(
				energy_consumption, renewable_percentage, carbon_footprint
			)
		
		# Overall efficiency score
		efficiency_metrics["overall_efficiency_score"] = self._calculate_overall_efficiency_score(efficiency_metrics)
		
		return efficiency_metrics
	
	def calculate_waste_efficiency(self, waste_data, activity_data):
		"""Calculate waste efficiency metrics"""
		if not waste_data or not activity_data:
			return {}
		
		efficiency_metrics = {}
		
		waste_generated = flt(waste_data.get("waste_generated", 0))
		activity_value = flt(activity_data.get("activity_value", 0))
		
		if waste_generated > 0 and activity_value > 0:
			# Waste intensity (waste per unit of activity)
			efficiency_metrics["waste_intensity"] = waste_generated / activity_value
			
			# Waste efficiency score (lower intensity = higher score)
			efficiency_metrics["waste_efficiency_score"] = max(0, 100 - (efficiency_metrics["waste_intensity"] * 10))
		
		# Recycling rate
		recycled_waste = flt(waste_data.get("recycled_waste", 0))
		if waste_generated > 0:
			efficiency_metrics["recycling_rate"] = (recycled_waste / waste_generated) * 100
		
		return efficiency_metrics
	
	def calculate_water_efficiency(self, water_data, activity_data):
		"""Calculate water efficiency metrics"""
		if not water_data or not activity_data:
			return {}
		
		efficiency_metrics = {}
		
		water_consumption = flt(water_data.get("water_consumption", 0))
		activity_value = flt(activity_data.get("activity_value", 0))
		
		if water_consumption > 0 and activity_value > 0:
			# Water intensity (water per unit of activity)
			efficiency_metrics["water_intensity"] = water_consumption / activity_value
			
			# Water efficiency score (lower intensity = higher score)
			efficiency_metrics["water_efficiency_score"] = max(0, 100 - (efficiency_metrics["water_intensity"] * 10))
		
		return efficiency_metrics
	
	def calculate_sustainability_score(self, metrics_data):
		"""Calculate overall sustainability score from various metrics"""
		if not metrics_data:
			return 0
		
		scores = []
		weights = []
		
		# Energy efficiency score (40% weight)
		if "energy_efficiency_score" in metrics_data:
			scores.append(flt(metrics_data["energy_efficiency_score"]))
			weights.append(0.4)
		
		# Carbon efficiency score (30% weight)
		if "carbon_efficiency_score" in metrics_data:
			scores.append(flt(metrics_data["carbon_efficiency_score"]))
			weights.append(0.3)
		
		# Waste efficiency score (20% weight)
		if "waste_efficiency_score" in metrics_data:
			scores.append(flt(metrics_data["waste_efficiency_score"]))
			weights.append(0.2)
		
		# Water efficiency score (10% weight)
		if "water_efficiency_score" in metrics_data:
			scores.append(flt(metrics_data["water_efficiency_score"]))
			weights.append(0.1)
		
		if not scores:
			return 0
		
		# Calculate weighted average
		total_weight = sum(weights)
		if total_weight > 0:
			return sum(score * weight for score, weight in zip(scores, weights)) / total_weight
		
		return 0
	
	def calculate_carbon_savings(self, baseline_data, current_data):
		"""Calculate carbon savings compared to baseline"""
		if not baseline_data or not current_data:
			return {}
		
		baseline_emissions = flt(baseline_data.get("total_emissions", 0))
		current_emissions = flt(current_data.get("total_emissions", 0))
		
		if baseline_emissions <= 0:
			return {}
		
		absolute_savings = baseline_emissions - current_emissions
		percentage_savings = (absolute_savings / baseline_emissions) * 100
		
		return {
			"absolute_savings": absolute_savings,
			"percentage_savings": percentage_savings,
			"baseline_emissions": baseline_emissions,
			"current_emissions": current_emissions
		}
	
	def calculate_energy_savings(self, baseline_data, current_data):
		"""Calculate energy savings compared to baseline"""
		if not baseline_data or not current_data:
			return {}
		
		baseline_consumption = flt(baseline_data.get("consumption_value", 0))
		current_consumption = flt(current_data.get("consumption_value", 0))
		
		if baseline_consumption <= 0:
			return {}
		
		absolute_savings = baseline_consumption - current_consumption
		percentage_savings = (absolute_savings / baseline_consumption) * 100
		
		return {
			"absolute_savings": absolute_savings,
			"percentage_savings": percentage_savings,
			"baseline_consumption": baseline_consumption,
			"current_consumption": current_consumption
		}
	
	def _get_emission_factors(self, activity_type, module, date):
		"""Get emission factors for specific activity type and module"""
		factors = []
		
		# Get factors for the specific module
		if activity_type in self.emission_factors and module in self.emission_factors[activity_type]:
			factors.extend(self.emission_factors[activity_type][module])
		
		# Get factors for "All" module
		if activity_type in self.emission_factors and "All" in self.emission_factors[activity_type]:
			factors.extend(self.emission_factors[activity_type]["All"])
		
		# Filter by date validity
		valid_factors = []
		for factor in factors:
			if self._is_factor_valid_for_date(factor, date):
				valid_factors.append(factor)
		
		return valid_factors
	
	def _is_factor_valid_for_date(self, factor, date):
		"""Check if emission factor is valid for given date"""
		if not factor.is_active:
			return False
		
		if factor.valid_from and date < factor.valid_from:
			return False
		
		if factor.valid_to and date > factor.valid_to:
			return False
		
		return True
	
	def _calculate_renewable_impact(self, energy_consumption, renewable_percentage, carbon_footprint):
		"""Calculate the impact of renewable energy usage"""
		if not energy_consumption or not renewable_percentage:
			return {}
		
		renewable_energy = energy_consumption * (renewable_percentage / 100)
		conventional_energy = energy_consumption - renewable_energy
		
		# Estimate carbon savings from renewable energy
		# Assuming 90% reduction in carbon footprint for renewable energy
		carbon_savings = carbon_footprint * (renewable_percentage / 100) * 0.9
		
		return {
			"renewable_energy": renewable_energy,
			"conventional_energy": conventional_energy,
			"carbon_savings": carbon_savings,
			"renewable_percentage": renewable_percentage
		}
	
	def _calculate_overall_efficiency_score(self, efficiency_metrics):
		"""Calculate overall efficiency score from individual metrics"""
		scores = []
		
		for key, value in efficiency_metrics.items():
			if key.endswith("_score") and isinstance(value, (int, float)):
				scores.append(flt(value))
		
		if not scores:
			return 0
		
		return sum(scores) / len(scores)


# Convenience functions
@frappe.whitelist()
def get_calculation_engine(company=None):
	"""Get Sustainability Calculation Engine instance"""
	return SustainabilityCalculationEngine(company)


@frappe.whitelist()
def calculate_carbon_footprint(activity_data, activity_type, module="All", date=None):
	"""Calculate carbon footprint for given activity data"""
	engine = SustainabilityCalculationEngine()
	return engine.calculate_carbon_footprint(activity_data, activity_type, module, date)


@frappe.whitelist()
def calculate_energy_efficiency(energy_data, activity_data):
	"""Calculate energy efficiency metrics"""
	engine = SustainabilityCalculationEngine()
	return engine.calculate_energy_efficiency(energy_data, activity_data)


@frappe.whitelist()
def calculate_sustainability_score(metrics_data):
	"""Calculate overall sustainability score"""
	engine = SustainabilityCalculationEngine()
	return engine.calculate_sustainability_score(metrics_data)
