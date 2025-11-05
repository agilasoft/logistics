# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime, getdate
from frappe import _


class EnergyConsumption(Document):
	def before_save(self):
		"""Calculate derived values before saving"""
		self.calculate_total_cost()
		self.calculate_carbon_footprint()
		self.calculate_carbon_intensity()
	
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
			"Petrol": 0.25,  # kg CO2 per kWh
			"Solar": 0.05,  # kg CO2 per kWh (including manufacturing)
			"Wind": 0.01,  # kg CO2 per kWh (including manufacturing)
			"Hydro": 0.01,  # kg CO2 per kWh (including infrastructure)
			"Other": 0.3  # Default factor
		}
		
		if self.consumption_value and self.energy_type:
			factor = carbon_factors.get(self.energy_type, 0.3)
			base_carbon = flt(self.consumption_value) * factor
			
			# Adjust for renewable energy percentage
			renewable_pct = flt(self.renewable_percentage or 0) / 100
			renewable_reduction = base_carbon * renewable_pct * 0.9  # 90% reduction for renewable
			
			self.carbon_footprint = max(0, base_carbon - renewable_reduction)
		else:
			self.carbon_footprint = 0
	
	def calculate_carbon_intensity(self):
		"""Calculate carbon intensity per unit of energy"""
		if self.consumption_value and self.carbon_footprint:
			self.carbon_intensity = self.carbon_footprint / self.consumption_value
		else:
			self.carbon_intensity = 0
	
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
		if not self.renewable_percentage or not self.consumption_value:
			return 0
		
		# Calculate carbon savings from renewable energy
		renewable_pct = flt(self.renewable_percentage) / 100
		base_carbon = self.carbon_footprint / (1 - renewable_pct * 0.9) if renewable_pct < 1 else 0
		carbon_savings = base_carbon * renewable_pct * 0.9
		
		return {
			"carbon_savings": carbon_savings,
			"renewable_energy_used": self.consumption_value * renewable_pct,
			"percentage": self.renewable_percentage
		}
	
	def validate_data(self):
		"""Validate energy consumption data"""
		# Validate date
		if self.date and self.date > getdate():
			frappe.throw(_("Date cannot be in the future"))
		
		# Validate consumption value is positive
		if self.consumption_value and self.consumption_value <= 0:
			frappe.throw(_("Consumption value must be positive"))
		
		# Validate renewable percentage
		if self.renewable_percentage and (self.renewable_percentage < 0 or self.renewable_percentage > 100):
			frappe.throw(_("Renewable Energy Percentage must be between 0 and 100"))


@frappe.whitelist()
def get_energy_consumption_summary(module=None, branch=None, facility=None, from_date=None, to_date=None):
	"""Get energy consumption summary for a specific module or all modules"""
	
	filters = {}
	if module:
		filters["module"] = module
	if branch:
		filters["branch"] = branch
	if facility:
		filters["facility"] = facility
	if from_date:
		filters["date"] = [">=", from_date]
	if to_date:
		filters["date"] = ["<=", to_date]
	
	# Get energy consumption data
	energy_data = frappe.get_all("Energy Consumption",
		filters=filters,
		fields=["*"],
		order_by="date desc"
	)
	
	# Calculate summary statistics
	summary = {
		"total_records": len(energy_data),
		"total_consumption": 0,
		"total_cost": 0,
		"total_carbon_footprint": 0,
		"average_renewable_percentage": 0,
		"energy_type_breakdown": {},
		"carbon_intensity_trend": "stable"
	}
	
	if energy_data:
		summary["total_consumption"] = sum(flt(e.consumption_value) for e in energy_data)
		summary["total_cost"] = sum(flt(e.total_cost) for e in energy_data)
		summary["total_carbon_footprint"] = sum(flt(e.carbon_footprint) for e in energy_data)
		summary["average_renewable_percentage"] = sum(flt(e.renewable_percentage) for e in energy_data) / len(energy_data)
		
		# Calculate energy type breakdown
		for data in energy_data:
			energy_type = data.energy_type or "Unknown"
			if energy_type not in summary["energy_type_breakdown"]:
				summary["energy_type_breakdown"][energy_type] = {
					"consumption": 0,
					"cost": 0,
					"carbon_footprint": 0
				}
			summary["energy_type_breakdown"][energy_type]["consumption"] += flt(data.consumption_value)
			summary["energy_type_breakdown"][energy_type]["cost"] += flt(data.total_cost)
			summary["energy_type_breakdown"][energy_type]["carbon_footprint"] += flt(data.carbon_footprint)
	
	return {
		"energy_data": energy_data,
		"summary": summary
	}


@frappe.whitelist()
def create_energy_consumption(module, reference_doctype=None, reference_name=None, **kwargs):
	"""Create a new energy consumption record"""
	
	doc = frappe.new_doc("Energy Consumption")
	doc.module = module
	doc.date = kwargs.get("date", getdate())
	doc.reference_doctype = reference_doctype
	doc.reference_name = reference_name
	doc.branch = kwargs.get("branch")
	doc.facility = kwargs.get("facility")
	doc.company = kwargs.get("company", frappe.defaults.get_user_default("Company"))
	
	# Set energy data
	doc.energy_type = kwargs.get("energy_type", "Electricity")
	doc.consumption_value = flt(kwargs.get("consumption_value"))
	doc.unit_of_measure = kwargs.get("unit_of_measure", "kWh")
	doc.cost_per_unit = flt(kwargs.get("cost_per_unit", 0))
	doc.renewable_percentage = flt(kwargs.get("renewable_percentage", 0))
	
	doc.notes = kwargs.get("notes")
	
	doc.insert(ignore_permissions=True)
	return doc.name
