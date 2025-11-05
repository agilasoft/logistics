# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime, getdate
from frappe import _


class CarbonFootprint(Document):
	def before_save(self):
		"""Calculate net emissions and validate data before saving"""
		self.calculate_net_emissions()
		self.validate_data()
	
	def calculate_net_emissions(self):
		"""Calculate net emissions after carbon offset"""
		total_emissions = flt(self.total_emissions) or 0
		carbon_offset = flt(self.carbon_offset) or 0
		self.net_emissions = max(0, total_emissions - carbon_offset)
	
	def validate_data(self):
		"""Validate carbon footprint data"""
		# Validate date
		if self.date and self.date > getdate():
			frappe.throw(_("Date cannot be in the future"))
		
		# Validate emissions are positive
		if self.total_emissions and self.total_emissions < 0:
			frappe.throw(_("Total emissions cannot be negative"))
		
		# Validate carbon offset is not negative
		if self.carbon_offset and self.carbon_offset < 0:
			frappe.throw(_("Carbon offset cannot be negative"))
		
		# Validate carbon offset doesn't exceed total emissions
		if self.carbon_offset and self.total_emissions and self.carbon_offset > self.total_emissions:
			frappe.throw(_("Carbon offset cannot exceed total emissions"))
	
	def get_emission_intensity(self, activity_value, activity_unit="kg"):
		"""Calculate emission intensity per unit of activity"""
		if not self.total_emissions or not activity_value:
			return 0
		
		return self.total_emissions / activity_value
	
	def get_carbon_efficiency_rating(self):
		"""Get carbon efficiency rating based on emissions"""
		if not self.total_emissions:
			return "No Data"
		
		# This is a simplified rating system - can be enhanced with industry benchmarks
		if self.total_emissions <= 100:
			return "Excellent"
		elif self.total_emissions <= 500:
			return "Good"
		elif self.total_emissions <= 1000:
			return "Fair"
		elif self.total_emissions <= 2000:
			return "Poor"
		else:
			return "Very Poor"
	
	def get_reduction_potential(self):
		"""Calculate potential carbon reduction based on best practices"""
		# This is a simplified calculation - can be enhanced with more sophisticated logic
		base_emissions = self.total_emissions or 0
		
		# Assume 20% reduction potential through efficiency measures
		efficiency_reduction = base_emissions * 0.20
		
		# Assume 30% reduction potential through renewable energy
		renewable_reduction = base_emissions * 0.30
		
		# Assume 10% reduction potential through waste reduction
		waste_reduction = base_emissions * 0.10
		
		return {
			"efficiency_reduction": efficiency_reduction,
			"renewable_reduction": renewable_reduction,
			"waste_reduction": waste_reduction,
			"total_potential": efficiency_reduction + renewable_reduction + waste_reduction
		}


@frappe.whitelist()
def get_carbon_footprint_summary(module=None, branch=None, facility=None, from_date=None, to_date=None):
	"""Get carbon footprint summary for a specific module or all modules"""
	
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
	
	# Get carbon footprint data
	carbon_data = frappe.get_all("Carbon Footprint",
		filters=filters,
		fields=["*"],
		order_by="date desc"
	)
	
	# Calculate summary statistics
	summary = {
		"total_records": len(carbon_data),
		"total_emissions": 0,
		"total_carbon_offset": 0,
		"net_emissions": 0,
		"average_emissions": 0,
		"scope_breakdown": {},
		"verification_breakdown": {}
	}
	
	if carbon_data:
		summary["total_emissions"] = sum(flt(c.total_emissions) for c in carbon_data)
		summary["total_carbon_offset"] = sum(flt(c.carbon_offset) for c in carbon_data)
		summary["net_emissions"] = sum(flt(c.net_emissions) for c in carbon_data)
		summary["average_emissions"] = summary["total_emissions"] / len(carbon_data)
		
		# Calculate scope breakdown
		for data in carbon_data:
			scope = data.scope or "Unknown"
			if scope not in summary["scope_breakdown"]:
				summary["scope_breakdown"][scope] = 0
			summary["scope_breakdown"][scope] += flt(data.total_emissions)
		
		# Calculate verification breakdown
		for data in carbon_data:
			status = data.verification_status or "Not Verified"
			if status not in summary["verification_breakdown"]:
				summary["verification_breakdown"][status] = 0
			summary["verification_breakdown"][status] += flt(data.total_emissions)
	
	return {
		"carbon_data": carbon_data,
		"summary": summary
	}


@frappe.whitelist()
def create_carbon_footprint(module, reference_doctype=None, reference_name=None, **kwargs):
	"""Create a new carbon footprint record"""
	
	doc = frappe.new_doc("Carbon Footprint")
	doc.module = module
	doc.date = kwargs.get("date", getdate())
	doc.reference_doctype = reference_doctype
	doc.reference_name = reference_name
	doc.branch = kwargs.get("branch")
	doc.facility = kwargs.get("facility")
	doc.company = kwargs.get("company", frappe.defaults.get_user_default("Company"))
	
	# Set emissions data
	doc.scope = kwargs.get("scope", "Combined")
	doc.total_emissions = flt(kwargs.get("total_emissions"))
	doc.carbon_offset = flt(kwargs.get("carbon_offset", 0))
	
	# Set calculation details
	doc.calculation_method = kwargs.get("calculation_method", "Emission Factor")
	doc.verification_status = kwargs.get("verification_status", "Not Verified")
	doc.verified_by = kwargs.get("verified_by")
	doc.verification_date = kwargs.get("verification_date")
	
	doc.notes = kwargs.get("notes")
	
	doc.insert(ignore_permissions=True)
	return doc.name
