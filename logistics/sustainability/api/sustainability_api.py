# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_days, add_months
from typing import Dict, List, Any, Optional
import json


class SustainabilityAPI:
	"""Centralized Sustainability API for all logistics modules"""
	
	def __init__(self, company=None):
		self.company = company or frappe.defaults.get_user_default("Company")
		self.settings = self._get_settings()
	
	def _get_settings(self):
		"""Get sustainability settings for the company"""
		try:
			return frappe.get_doc("Sustainability Settings", self.company)
		except frappe.DoesNotExistError:
			# Create default settings
			settings = frappe.new_doc("Sustainability Settings")
			settings.company = self.company
			settings.insert(ignore_permissions=True)
			return settings
	
	def create_sustainability_metric(self, module, reference_doctype=None, reference_name=None, **kwargs):
		"""Create a sustainability metric record"""
		doc = frappe.new_doc("Sustainability Metrics")
		doc.module = module
		doc.date = kwargs.get("date", getdate())
		doc.reference_doctype = reference_doctype
		doc.reference_name = reference_name
		doc.site = kwargs.get("site")
		doc.facility = kwargs.get("facility")
		doc.company = self.company
		
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
	
	def create_carbon_footprint(self, module, reference_doctype=None, reference_name=None, **kwargs):
		"""Create a carbon footprint record"""
		doc = frappe.new_doc("Carbon Footprint")
		doc.module = module
		doc.date = kwargs.get("date", getdate())
		doc.reference_doctype = reference_doctype
		doc.reference_name = reference_name
		doc.site = kwargs.get("site")
		doc.facility = kwargs.get("facility")
		doc.company = self.company
		
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
	
	def create_energy_consumption(self, module, reference_doctype=None, reference_name=None, **kwargs):
		"""Create an energy consumption record"""
		doc = frappe.new_doc("Energy Consumption")
		doc.module = module
		doc.date = kwargs.get("date", getdate())
		doc.reference_doctype = reference_doctype
		doc.reference_name = reference_name
		doc.site = kwargs.get("site")
		doc.facility = kwargs.get("facility")
		doc.company = self.company
		
		# Set energy data
		doc.energy_type = kwargs.get("energy_type", "Electricity")
		doc.consumption_value = flt(kwargs.get("consumption_value"))
		doc.unit_of_measure = kwargs.get("unit_of_measure", "kWh")
		doc.cost_per_unit = flt(kwargs.get("cost_per_unit", 0))
		doc.renewable_percentage = flt(kwargs.get("renewable_percentage", 0))
		
		doc.notes = kwargs.get("notes")
		
		doc.insert(ignore_permissions=True)
		return doc.name
	
	def calculate_carbon_footprint(self, activity_data, activity_type, module):
		"""Calculate carbon footprint for given activity data"""
		# Get emission factors
		emission_factors = self._get_emission_factors(activity_type, module)
		
		if not emission_factors:
			frappe.throw(_(f"No emission factors found for {activity_type} in {module} module"))
		
		total_emissions = 0
		emission_breakdown = []
		
		for factor in emission_factors:
			emission_value = flt(activity_data.get(factor.factor_name, 0)) * flt(factor.factor_value)
			total_emissions += emission_value
			
			emission_breakdown.append({
				"emission_source": factor.factor_name,
				"emission_value": emission_value,
				"unit_of_measure": factor.unit_of_measure,
				"emission_factor": factor.factor_value,
				"activity_data": flt(activity_data.get(factor.factor_name, 0))
			})
		
		return {
			"total_emissions": total_emissions,
			"emission_breakdown": emission_breakdown
		}
	
	def calculate_energy_efficiency(self, energy_data, activity_data):
		"""Calculate energy efficiency metrics"""
		if not energy_data or not activity_data:
			return {}
		
		efficiency_metrics = {}
		
		# Calculate energy intensity
		if energy_data.get("consumption_value") and activity_data.get("activity_value"):
			efficiency_metrics["energy_intensity"] = (
				flt(energy_data["consumption_value"]) / flt(activity_data["activity_value"])
			)
		
		# Calculate carbon intensity
		if energy_data.get("carbon_footprint") and activity_data.get("activity_value"):
			efficiency_metrics["carbon_intensity"] = (
				flt(energy_data["carbon_footprint"]) / flt(activity_data["activity_value"])
			)
		
		# Calculate efficiency score
		efficiency_metrics["efficiency_score"] = self._calculate_efficiency_score(efficiency_metrics)
		
		return efficiency_metrics
	
	def get_sustainability_dashboard_data(self, module=None, site=None, facility=None, from_date=None, to_date=None):
		"""Get comprehensive sustainability dashboard data"""
		filters = {"company": self.company}
		
		if module:
			filters["module"] = module
		if site:
			filters["site"] = site
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
		
		# Get carbon footprint data
		carbon_data = frappe.get_all("Carbon Footprint",
			filters=filters,
			fields=["*"],
			order_by="date desc"
		)
		
		# Get energy consumption data
		energy_data = frappe.get_all("Energy Consumption",
			filters=filters,
			fields=["*"],
			order_by="date desc"
		)
		
		# Calculate summary statistics
		summary = self._calculate_summary_statistics(metrics, carbon_data, energy_data)
		
		# Get trends
		trends = self._calculate_trends(metrics, carbon_data, energy_data)
		
		# Get compliance status
		compliance = self._get_compliance_status(module, site, facility)
		
		return {
			"metrics": metrics,
			"carbon_data": carbon_data,
			"energy_data": energy_data,
			"summary": summary,
			"trends": trends,
			"compliance": compliance
		}
	
	def _get_emission_factors(self, activity_type, module):
		"""Get emission factors for a specific activity type and module"""
		filters = {
			"category": activity_type,
			"is_active": 1
		}
		
		if module != "All":
			filters["module"] = ["in", [module, "All"]]
		
		return frappe.get_all("Emission Factors",
			filters=filters,
			fields=["*"],
			order_by="valid_from desc, creation desc"
		)
	
	def _calculate_efficiency_score(self, efficiency_metrics):
		"""Calculate overall efficiency score"""
		score = 0
		count = 0
		
		# Energy intensity score (lower is better)
		if efficiency_metrics.get("energy_intensity"):
			energy_score = max(0, 100 - (efficiency_metrics["energy_intensity"] * 10))
			score += energy_score
			count += 1
		
		# Carbon intensity score (lower is better)
		if efficiency_metrics.get("carbon_intensity"):
			carbon_score = max(0, 100 - (efficiency_metrics["carbon_intensity"] * 10))
			score += carbon_score
			count += 1
		
		return score / count if count > 0 else 0
	
	def _calculate_summary_statistics(self, metrics, carbon_data, energy_data):
		"""Calculate summary statistics"""
		summary = {
			"total_metrics": len(metrics),
			"total_carbon_records": len(carbon_data),
			"total_energy_records": len(energy_data),
			"total_energy_consumption": 0,
			"total_carbon_footprint": 0,
			"total_waste_generated": 0,
			"average_sustainability_score": 0,
			"average_renewable_percentage": 0
		}
		
		if metrics:
			summary["total_energy_consumption"] = sum(flt(m.energy_consumption) for m in metrics)
			summary["total_carbon_footprint"] = sum(flt(m.carbon_footprint) for m in metrics)
			summary["total_waste_generated"] = sum(flt(m.waste_generated) for m in metrics)
			summary["average_sustainability_score"] = sum(flt(m.sustainability_score) for m in metrics) / len(metrics)
			summary["average_renewable_percentage"] = sum(flt(m.renewable_energy_percentage) for m in metrics) / len(metrics)
		
		return summary
	
	def _calculate_trends(self, metrics, carbon_data, energy_data):
		"""Calculate trends over time"""
		trends = {
			"energy_trend": "stable",
			"carbon_trend": "stable",
			"waste_trend": "stable",
			"sustainability_trend": "stable"
		}
		
		# Calculate trends based on recent data
		if len(metrics) >= 2:
			recent_metrics = sorted(metrics, key=lambda x: x.date)[-2:]
			
			# Energy trend
			if recent_metrics[0].energy_consumption and recent_metrics[1].energy_consumption:
				if recent_metrics[0].energy_consumption > recent_metrics[1].energy_consumption:
					trends["energy_trend"] = "increasing"
				elif recent_metrics[0].energy_consumption < recent_metrics[1].energy_consumption:
					trends["energy_trend"] = "decreasing"
			
			# Carbon trend
			if recent_metrics[0].carbon_footprint and recent_metrics[1].carbon_footprint:
				if recent_metrics[0].carbon_footprint > recent_metrics[1].carbon_footprint:
					trends["carbon_trend"] = "increasing"
				elif recent_metrics[0].carbon_footprint < recent_metrics[1].carbon_footprint:
					trends["carbon_trend"] = "decreasing"
		
		return trends
	
	def _get_compliance_status(self, module=None, site=None, facility=None):
		"""Get compliance status"""
		filters = {"company": self.company}
		
		if module:
			filters["module"] = module
		if site:
			filters["site"] = site
		if facility:
			filters["facility"] = facility
		
		compliance_data = frappe.get_all("Sustainability Compliance",
			filters=filters,
			fields=["*"],
			order_by="expiry_date asc"
		)
		
		compliance_summary = {
			"total_compliance": len(compliance_data),
			"certified_count": 0,
			"expired_count": 0,
			"expiring_soon_count": 0,
			"compliant_count": 0
		}
		
		for data in compliance_data:
			if data.certification_status == "Certified":
				compliance_summary["certified_count"] += 1
			elif data.certification_status == "Expired":
				compliance_summary["expired_count"] += 1
			
			if data.compliance_status == "Compliant":
				compliance_summary["compliant_count"] += 1
			
			# Check if expiring soon
			if data.expiry_date:
				days_until_expiry = (data.expiry_date - getdate()).days
				if 0 <= days_until_expiry <= 30:
					compliance_summary["expiring_soon_count"] += 1
		
		return compliance_summary


# Convenience functions for easy access
@frappe.whitelist()
def get_sustainability_api(company=None):
	"""Get Sustainability API instance"""
	return SustainabilityAPI(company)


@frappe.whitelist()
def create_sustainability_metric(module, reference_doctype=None, reference_name=None, **kwargs):
	"""Create a sustainability metric record"""
	api = SustainabilityAPI()
	return api.create_sustainability_metric(module, reference_doctype, reference_name, **kwargs)


@frappe.whitelist()
def create_carbon_footprint(module, reference_doctype=None, reference_name=None, **kwargs):
	"""Create a carbon footprint record"""
	api = SustainabilityAPI()
	return api.create_carbon_footprint(module, reference_doctype, reference_name, **kwargs)


@frappe.whitelist()
def create_energy_consumption(module, reference_doctype=None, reference_name=None, **kwargs):
	"""Create an energy consumption record"""
	api = SustainabilityAPI()
	return api.create_energy_consumption(module, reference_doctype, reference_name, **kwargs)


@frappe.whitelist()
def get_sustainability_dashboard_data(module=None, site=None, facility=None, from_date=None, to_date=None):
	"""Get sustainability dashboard data"""
	api = SustainabilityAPI()
	return api.get_sustainability_dashboard_data(module, site, facility, from_date, to_date)
