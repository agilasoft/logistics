# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate


def get_context(context):
	"""Get context for sustainability configuration page"""
	context.title = _("Sustainability Configuration")
	context.settings = get_sustainability_settings()
	context.emission_factors = get_emission_factors_summary()
	context.integrated_modules = get_integrated_modules_status()
	context.compliance_status = get_compliance_status()


def get_sustainability_settings():
	"""Get sustainability settings for current company"""
	company = frappe.defaults.get_user_default("Company")
	
	try:
		settings = frappe.get_doc("Sustainability Settings", company)
		return settings
	except frappe.DoesNotExistError:
		# Create default settings
		settings = frappe.new_doc("Sustainability Settings")
		settings.company = company
		settings.insert(ignore_permissions=True)
		return settings


def get_emission_factors_summary():
	"""Get summary of emission factors"""
	factors = frappe.get_all("Emission Factors",
		filters={"is_active": 1},
		fields=["category", "module", "count(*) as count"],
		group_by="category, module"
	)
	
	summary = {}
	for factor in factors:
		category = factor.category or "Other"
		module = factor.module or "All"
		
		if category not in summary:
			summary[category] = {}
		summary[category][module] = factor.count
	
	return summary


def get_integrated_modules_status():
	"""Get status of integrated modules"""
	settings = get_sustainability_settings()
	
	modules = []
	for module in settings.integrated_modules:
		modules.append({
			"module_name": module.module_name,
			"enable_tracking": module.enable_tracking,
			"enable_carbon_tracking": module.enable_carbon_tracking,
			"enable_energy_tracking": module.enable_energy_tracking,
			"enable_waste_tracking": module.enable_waste_tracking,
			"auto_calculate": module.auto_calculate,
			"calculation_frequency": module.calculation_frequency
		})
	
	return modules


def get_compliance_status():
	"""Get compliance status summary"""
	company = frappe.defaults.get_user_default("Company")
	
	compliance_data = frappe.get_all("Sustainability Compliance",
		filters={"company": company},
		fields=["compliance_type", "certification_status", "compliance_status", "expiry_date"]
	)
	
	summary = {
		"total_compliance": len(compliance_data),
		"certified": 0,
		"expired": 0,
		"expiring_soon": 0,
		"compliant": 0
	}
	
	today = getdate()
	for data in compliance_data:
		if data.certification_status == "Certified":
			summary["certified"] += 1
		elif data.certification_status == "Expired":
			summary["expired"] += 1
		
		if data.compliance_status == "Compliant":
			summary["compliant"] += 1
		
		# Check if expiring soon (within 30 days)
		if data.expiry_date:
			days_until_expiry = (data.expiry_date - today).days
			if 0 <= days_until_expiry <= 30:
				summary["expiring_soon"] += 1
	
	return summary


@frappe.whitelist()
def setup_sustainability():
	"""Setup sustainability module"""
	from .setup_sustainability import setup_sustainability as setup_func
	setup_func()
	return {"status": "success", "message": "Sustainability module setup completed!"}


@frappe.whitelist()
def update_module_integration(module_name, **kwargs):
	"""Update module integration settings"""
	from .api import enable_module_integration
	return enable_module_integration(module_name, **kwargs)
