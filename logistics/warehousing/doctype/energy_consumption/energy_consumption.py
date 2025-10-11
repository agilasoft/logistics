# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime
from frappe import _


class EnergyConsumption(Document):
	def before_save(self):
		"""Calculate total cost and carbon footprint before saving"""
		self.calculate_total_cost()
		self.calculate_carbon_footprint()
	
	def calculate_total_cost(self):
		"""Calculate total cost based on consumption and cost per unit"""
		if self.consumption_value and self.cost_per_unit:
			self.total_cost = flt(self.consumption_value) * flt(self.cost_per_unit)
		else:
			self.total_cost = 0
	
	def calculate_carbon_footprint(self):
		"""Calculate carbon footprint based on energy type and consumption"""
		carbon_factors = {
			"Electricity": 0.4,  # kg CO2 per kWh
			"Natural Gas": 0.2,  # kg CO2 per kWh
			"Diesel": 0.27,  # kg CO2 per kWh
			"Solar": 0.05,  # kg CO2 per kWh (including manufacturing)
			"Wind": 0.01,  # kg CO2 per kWh (including manufacturing)
			"Hydro": 0.01,  # kg CO2 per kWh (including infrastructure)
			"Other": 0.3  # Default factor
		}
		
		if self.consumption_value and self.energy_type:
			factor = carbon_factors.get(self.energy_type, 0.3)
			self.carbon_footprint = flt(self.consumption_value) * factor
		else:
			self.carbon_footprint = 0
	
	def get_efficiency_score(self):
		"""Calculate energy efficiency score based on consumption per unit of work"""
		if not self.efficiency_metrics:
			return 0
		
		total_score = 0
		count = 0
		
		for metric in self.efficiency_metrics:
			if metric.efficiency_value and metric.target_value:
				score = (flt(metric.target_value) / flt(metric.efficiency_value)) * 100
				total_score += min(score, 100)  # Cap at 100%
				count += 1
		
		return total_score / count if count > 0 else 0
	
	def get_renewable_energy_impact(self):
		"""Calculate the impact of renewable energy usage"""
		if not self.renewable_percentage:
			return 0
		
		renewable_factor = flt(self.renewable_percentage) / 100
		base_carbon = self.carbon_footprint
		renewable_carbon = base_carbon * renewable_factor * 0.1  # 90% reduction for renewable
		non_renewable_carbon = base_carbon * (1 - renewable_factor)
		
		return {
			"total_carbon": base_carbon,
			"renewable_carbon": renewable_carbon,
			"non_renewable_carbon": non_renewable_carbon,
			"carbon_savings": base_carbon - (renewable_carbon + non_renewable_carbon)
		}


@frappe.whitelist()
def get_energy_efficiency_report(site=None, facility=None, from_date=None, to_date=None):
	"""Get energy efficiency report for a site or facility"""
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
		fields=["date", "energy_type", "consumption_value", "carbon_footprint", "total_cost", "renewable_percentage"],
		order_by="date desc"
	)
	
	# Calculate efficiency metrics
	total_consumption = sum(flt(d.consumption_value) for d in energy_data)
	total_carbon = sum(flt(d.carbon_footprint) for d in energy_data)
	total_cost = sum(flt(d.total_cost) for d in energy_data)
	avg_renewable = sum(flt(d.renewable_percentage or 0) for d in energy_data) / len(energy_data) if energy_data else 0
	
	return {
		"energy_data": energy_data,
		"summary": {
			"total_consumption": total_consumption,
			"total_carbon_footprint": total_carbon,
			"total_cost": total_cost,
			"average_renewable_percentage": avg_renewable,
			"carbon_intensity": total_carbon / total_consumption if total_consumption > 0 else 0
		}
	}


@frappe.whitelist()
def calculate_carbon_savings(site=None, facility=None, from_date=None, to_date=None):
	"""Calculate carbon savings from renewable energy and efficiency measures"""
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
		fields=["carbon_footprint", "renewable_percentage", "energy_type"]
	)
	
	total_savings = 0
	renewable_savings = 0
	efficiency_savings = 0
	
	for data in energy_data:
		base_carbon = flt(data.carbon_footprint)
		renewable_pct = flt(data.renewable_percentage or 0) / 100
		
		# Calculate renewable energy savings (90% reduction for renewable)
		renewable_saving = base_carbon * renewable_pct * 0.9
		renewable_savings += renewable_saving
		
		# Calculate efficiency savings (assume 20% improvement from efficiency measures)
		efficiency_saving = base_carbon * 0.2
		efficiency_savings += efficiency_saving
		
		total_savings += renewable_saving + efficiency_saving
	
	return {
		"total_carbon_savings": total_savings,
		"renewable_energy_savings": renewable_savings,
		"efficiency_savings": efficiency_savings,
		"total_energy_consumption": sum(flt(d.carbon_footprint) for d in energy_data),
		"savings_percentage": (total_savings / sum(flt(d.carbon_footprint) for d in energy_data)) * 100 if energy_data else 0
	}
