# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime, getdate
from frappe import _


class SustainabilityMetrics(Document):
	def before_save(self):
		"""Calculate scores and validate data before saving"""
		self.calculate_scores()
		self.validate_data()
	
	def calculate_scores(self):
		"""Calculate sustainability scores based on metrics"""
		# Calculate energy efficiency score
		if self.energy_consumption and self.energy_consumption > 0:
			# This is a simplified calculation - can be enhanced with more sophisticated logic
			self.energy_efficiency_score = min(100, max(0, 100 - (self.energy_consumption / 100)))
		else:
			self.energy_efficiency_score = 0
		
		# Calculate carbon efficiency score
		if self.carbon_footprint and self.carbon_footprint > 0:
			# This is a simplified calculation - can be enhanced with more sophisticated logic
			self.carbon_efficiency_score = min(100, max(0, 100 - (self.carbon_footprint / 10)))
		else:
			self.carbon_efficiency_score = 0
		
		# Calculate waste efficiency score
		if self.waste_generated and self.waste_generated > 0:
			# This is a simplified calculation - can be enhanced with more sophisticated logic
			self.waste_efficiency_score = min(100, max(0, 100 - (self.waste_generated / 5)))
		else:
			self.waste_efficiency_score = 0
		
		# Calculate overall sustainability score (weighted average)
		scores = []
		weights = []
		
		if self.energy_efficiency_score > 0:
			scores.append(self.energy_efficiency_score)
			weights.append(0.4)  # 40% weight for energy
		
		if self.carbon_efficiency_score > 0:
			scores.append(self.carbon_efficiency_score)
			weights.append(0.4)  # 40% weight for carbon
		
		if self.waste_efficiency_score > 0:
			scores.append(self.waste_efficiency_score)
			weights.append(0.2)  # 20% weight for waste
		
		if scores and weights:
			total_weight = sum(weights)
			if total_weight > 0:
				self.sustainability_score = sum(score * weight for score, weight in zip(scores, weights)) / total_weight
			else:
				self.sustainability_score = 0
		else:
			self.sustainability_score = 0
	
	def validate_data(self):
		"""Validate sustainability data"""
		# Validate date
		if self.date and self.date > getdate():
			frappe.throw(_("Date cannot be in the future"))
		
		# Validate scores are within range
		score_fields = ['sustainability_score', 'energy_efficiency_score', 'carbon_efficiency_score', 'waste_efficiency_score']
		for field in score_fields:
			value = getattr(self, field, 0)
			if value and (value < 0 or value > 100):
				frappe.throw(_(f"{field.replace('_', ' ').title()} must be between 0 and 100"))
		
		# Validate renewable energy percentage
		if self.renewable_energy_percentage and (self.renewable_energy_percentage < 0 or self.renewable_energy_percentage > 100):
			frappe.throw(_("Renewable Energy Percentage must be between 0 and 100"))
	
	def get_sustainability_rating(self):
		"""Get sustainability rating based on overall score"""
		score = self.sustainability_score or 0
		
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
	
	def get_improvement_recommendations(self):
		"""Get improvement recommendations based on current metrics"""
		recommendations = []
		
		if self.energy_efficiency_score < 70:
			recommendations.append("Improve energy efficiency through better equipment and processes")
		
		if self.carbon_efficiency_score < 70:
			recommendations.append("Reduce carbon footprint through renewable energy and efficiency measures")
		
		if self.waste_efficiency_score < 70:
			recommendations.append("Implement waste reduction and recycling programs")
		
		if self.renewable_energy_percentage < 30:
			recommendations.append("Increase renewable energy usage")
		
		return recommendations


@frappe.whitelist()
def get_sustainability_dashboard_data(module=None, branch=None, facility=None, from_date=None, to_date=None):
	"""Get sustainability dashboard data for a specific module or all modules"""
	
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
	
	# Get sustainability metrics
	metrics = frappe.get_all("Sustainability Metrics",
		filters=filters,
		fields=["*"],
		order_by="date desc"
	)
	
	# Calculate summary statistics
	summary = {
		"total_records": len(metrics),
		"average_sustainability_score": 0,
		"average_energy_efficiency": 0,
		"average_carbon_efficiency": 0,
		"average_waste_efficiency": 0,
		"total_energy_consumption": 0,
		"total_carbon_footprint": 0,
		"total_waste_generated": 0,
		"average_renewable_percentage": 0
	}
	
	if metrics:
		summary["average_sustainability_score"] = sum(flt(m.sustainability_score) for m in metrics) / len(metrics)
		summary["average_energy_efficiency"] = sum(flt(m.energy_efficiency_score) for m in metrics) / len(metrics)
		summary["average_carbon_efficiency"] = sum(flt(m.carbon_efficiency_score) for m in metrics) / len(metrics)
		summary["average_waste_efficiency"] = sum(flt(m.waste_efficiency_score) for m in metrics) / len(metrics)
		summary["total_energy_consumption"] = sum(flt(m.energy_consumption) for m in metrics)
		summary["total_carbon_footprint"] = sum(flt(m.carbon_footprint) for m in metrics)
		summary["total_waste_generated"] = sum(flt(m.waste_generated) for m in metrics)
		summary["average_renewable_percentage"] = sum(flt(m.renewable_energy_percentage) for m in metrics) / len(metrics)
	
	return {
		"metrics": metrics,
		"summary": summary
	}


@frappe.whitelist()
def create_sustainability_metric(module, reference_doctype=None, reference_name=None, **kwargs):
	"""Create a new sustainability metric record"""
	
	doc = frappe.new_doc("Sustainability Metrics")
	doc.module = module
	doc.date = kwargs.get("date", getdate())
	doc.reference_doctype = reference_doctype
	doc.reference_name = reference_name
	doc.branch = kwargs.get("branch")
	doc.company = kwargs.get("company", frappe.defaults.get_user_default("Company"))
	doc.facility = kwargs.get("facility")
	
	# Set metrics
	doc.energy_consumption = flt(kwargs.get("energy_consumption"))
	doc.carbon_footprint = flt(kwargs.get("carbon_footprint"))
	doc.waste_generated = flt(kwargs.get("waste_generated"))
	doc.water_consumption = flt(kwargs.get("water_consumption"))
	doc.renewable_energy_percentage = flt(kwargs.get("renewable_energy_percentage"))
	
	# Set compliance status
	doc.compliance_status = kwargs.get("compliance_status", "Not Applicable")
	doc.certification_status = kwargs.get("certification_status", "Not Certified")
	doc.verification_status = kwargs.get("verification_status", "Not Verified")
	
	doc.notes = kwargs.get("notes")
	
	doc.insert(ignore_permissions=True)
	return doc.name
