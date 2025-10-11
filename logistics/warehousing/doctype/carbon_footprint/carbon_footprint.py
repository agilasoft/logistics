# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime
from frappe import _


class CarbonFootprint(Document):
	def before_save(self):
		"""Calculate total emissions and validate data before saving"""
		self.calculate_total_emissions()
		self.validate_emission_data()
	
	def calculate_total_emissions(self):
		"""Calculate total emissions from breakdown"""
		if self.emission_breakdown:
			total = 0
			for breakdown in self.emission_breakdown:
				total += flt(breakdown.emission_value or 0)
			self.total_emissions = total
		else:
			self.total_emissions = 0
	
	def validate_emission_data(self):
		"""Validate emission data for consistency"""
		if self.total_emissions < 0:
			frappe.throw("Total emissions cannot be negative")
		
		# Validate scope-specific requirements
		if self.scope == "Scope 1" and not self.has_direct_emissions():
			frappe.msgprint("Scope 1 should include direct emissions from owned sources")
		
		if self.scope == "Scope 2" and not self.has_electricity_emissions():
			frappe.msgprint("Scope 2 should include indirect emissions from purchased energy")
	
	def has_direct_emissions(self):
		"""Check if record has direct emissions (Scope 1)"""
		direct_sources = ["Natural Gas", "Diesel", "Gasoline", "Propane"]
		if self.emission_breakdown:
			for breakdown in self.emission_breakdown:
				if breakdown.emission_source in direct_sources:
					return True
		return False
	
	def has_electricity_emissions(self):
		"""Check if record has electricity emissions (Scope 2)"""
		if self.emission_breakdown:
			for breakdown in self.emission_breakdown:
				if breakdown.emission_source == "Electricity":
					return True
		return False
	
	def get_emission_intensity(self, activity_data=None):
		"""Calculate emission intensity per unit of activity"""
		if not activity_data or self.total_emissions == 0:
			return 0
		
		return flt(self.total_emissions) / flt(activity_data)
	
	def get_reduction_progress(self):
		"""Calculate progress towards reduction targets"""
		if not self.reduction_targets:
			return {}
		
		progress = {}
		for target in self.reduction_targets:
			if target.target_value and target.baseline_value:
				reduction_achieved = flt(target.baseline_value) - flt(self.total_emissions)
				reduction_target = flt(target.baseline_value) - flt(target.target_value)
				
				if reduction_target > 0:
					progress_percentage = (reduction_achieved / reduction_target) * 100
					progress[target.target_name] = {
						"target_reduction": reduction_target,
						"achieved_reduction": reduction_achieved,
						"progress_percentage": min(progress_percentage, 100)
					}
		
		return progress


@frappe.whitelist()
def get_carbon_footprint_report(site=None, facility=None, from_date=None, to_date=None, scope=None):
	"""Get comprehensive carbon footprint report"""
	filters = {}
	if site:
		filters["site"] = site
	if facility:
		filters["facility"] = facility
	if from_date:
		filters["date"] = [">=", from_date]
	if to_date:
		filters["date"] = ["<=", to_date]
	if scope:
		filters["scope"] = scope
	
	carbon_data = frappe.get_all("Carbon Footprint", 
		filters=filters,
		fields=["date", "scope", "total_emissions", "verification_status"],
		order_by="date desc"
	)
	
	# Calculate summary metrics
	total_emissions = sum(flt(d.total_emissions) for d in carbon_data)
	scope_breakdown = {}
	verification_breakdown = {}
	
	for data in carbon_data:
		scope = data.scope
		verification = data.verification_status or "Not Verified"
		
		if scope not in scope_breakdown:
			scope_breakdown[scope] = 0
		scope_breakdown[scope] += flt(data.total_emissions)
		
		if verification not in verification_breakdown:
			verification_breakdown[verification] = 0
		verification_breakdown[verification] += flt(data.total_emissions)
	
	return {
		"carbon_data": carbon_data,
		"summary": {
			"total_emissions": total_emissions,
			"scope_breakdown": scope_breakdown,
			"verification_breakdown": verification_breakdown,
			"average_daily_emissions": total_emissions / len(carbon_data) if carbon_data else 0
		}
	}


@frappe.whitelist()
def calculate_carbon_savings(site=None, facility=None, from_date=None, to_date=None):
	"""Calculate carbon savings from various initiatives"""
	filters = {}
	if site:
		filters["site"] = site
	if facility:
		filters["facility"] = facility
	if from_date:
		filters["date"] = [">=", from_date]
	if to_date:
		filters["date"] = ["<=", to_date]
	
	# Get energy consumption data for renewable energy savings
	energy_data = frappe.get_all("Energy Consumption", 
		filters=filters,
		fields=["carbon_footprint", "renewable_percentage", "energy_type"]
	)
	
	# Get carbon footprint data for baseline
	carbon_data = frappe.get_all("Carbon Footprint", 
		filters=filters,
		fields=["total_emissions", "scope"]
	)
	
	total_savings = 0
	renewable_savings = 0
	efficiency_savings = 0
	
	# Calculate renewable energy savings
	for energy in energy_data:
		base_carbon = flt(energy.carbon_footprint)
		renewable_pct = flt(energy.renewable_percentage or 0) / 100
		renewable_saving = base_carbon * renewable_pct * 0.9  # 90% reduction for renewable
		renewable_savings += renewable_saving
	
	# Calculate efficiency savings (assume 15% improvement from efficiency measures)
	for carbon in carbon_data:
		efficiency_saving = flt(carbon.total_emissions) * 0.15
		efficiency_savings += efficiency_saving
	
	total_savings = renewable_savings + efficiency_savings
	total_emissions = sum(flt(c.total_emissions) for c in carbon_data)
	
	return {
		"total_carbon_savings": total_savings,
		"renewable_energy_savings": renewable_savings,
		"efficiency_savings": efficiency_savings,
		"total_emissions": total_emissions,
		"savings_percentage": (total_savings / total_emissions) * 100 if total_emissions > 0 else 0,
		"carbon_intensity_reduction": (total_savings / total_emissions) * 100 if total_emissions > 0 else 0
	}
