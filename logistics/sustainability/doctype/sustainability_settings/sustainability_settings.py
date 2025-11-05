# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime, getdate
from frappe import _


class SustainabilitySettings(Document):
	def validate(self):
		"""Validate sustainability settings"""
		self.validate_notification_days()
		self.validate_integrated_modules()
	
	def validate_notification_days(self):
		"""Validate notification days are positive"""
		if self.expiry_notification_days and self.expiry_notification_days < 0:
			frappe.throw(_("Expiry notification days must be positive"))
		
		if self.audit_notification_days and self.audit_notification_days < 0:
			frappe.throw(_("Audit notification days must be positive"))
	
	def validate_integrated_modules(self):
		"""Validate integrated modules configuration"""
		if not self.enable_module_integration:
			return
		
		# Check if integrated modules are properly configured
		for module in self.integrated_modules:
			if not module.module_name:
				frappe.throw(_("Module name is required for integrated modules"))
			
			if not module.enable_tracking:
				continue
			
			# Validate module-specific settings
			if module.module_name == "Transport" and not module.enable_carbon_tracking:
				frappe.throw(_("Carbon tracking must be enabled for Transport module"))
			
			if module.module_name == "Warehousing" and not module.enable_energy_tracking:
				frappe.throw(_("Energy tracking must be enabled for Warehousing module"))
	
	def get_default_emission_factor(self, factor_name):
		"""Get default emission factor by name"""
		for factor in self.default_emission_factors:
			if factor.factor_name == factor_name:
				return factor.factor_value
		return None
	
	def get_integrated_module_config(self, module_name):
		"""Get configuration for a specific integrated module"""
		for module in self.integrated_modules:
			if module.module_name == module_name:
				return {
					"enable_tracking": module.enable_tracking,
					"enable_carbon_tracking": module.enable_carbon_tracking,
					"enable_energy_tracking": module.enable_energy_tracking,
					"enable_waste_tracking": module.enable_waste_tracking,
					"auto_calculate": module.auto_calculate,
					"calculation_frequency": module.calculation_frequency
				}
		return None
	
	def is_module_integrated(self, module_name):
		"""Check if a module is integrated for sustainability tracking"""
		if not self.enable_module_integration:
			return False
		
		for module in self.integrated_modules:
			if module.module_name == module_name and module.enable_tracking:
				return True
		return False


@frappe.whitelist()
def get_sustainability_settings(company=None):
	"""Get sustainability settings for a company"""
	if not company:
		company = frappe.defaults.get_user_default("Company")
	
	try:
		settings = frappe.get_doc("Sustainability Settings", company)
		return settings
	except frappe.DoesNotExistError:
		# Create default settings if they don't exist
		settings = frappe.new_doc("Sustainability Settings")
		settings.company = company
		settings.insert(ignore_permissions=True)
		return settings


@frappe.whitelist()
def update_sustainability_settings(company, **kwargs):
	"""Update sustainability settings for a company"""
	settings = get_sustainability_settings(company)
	
	# Update fields
	for key, value in kwargs.items():
		if hasattr(settings, key):
			setattr(settings, key, value)
	
	settings.save(ignore_permissions=True)
	return settings.name


@frappe.whitelist()
def enable_module_integration(module_name, **kwargs):
	"""Enable sustainability integration for a specific module"""
	settings = get_sustainability_settings()
	
	# Check if module is already integrated
	for module in settings.integrated_modules:
		if module.module_name == module_name:
			# Update existing module
			module.enable_tracking = kwargs.get("enable_tracking", True)
			module.enable_carbon_tracking = kwargs.get("enable_carbon_tracking", True)
			module.enable_energy_tracking = kwargs.get("enable_energy_tracking", True)
			module.enable_waste_tracking = kwargs.get("enable_waste_tracking", True)
			module.auto_calculate = kwargs.get("auto_calculate", True)
			module.calculation_frequency = kwargs.get("calculation_frequency", "Daily")
			break
	else:
		# Add new module
		settings.append("integrated_modules", {
			"module_name": module_name,
			"enable_tracking": kwargs.get("enable_tracking", True),
			"enable_carbon_tracking": kwargs.get("enable_carbon_tracking", True),
			"enable_energy_tracking": kwargs.get("enable_energy_tracking", True),
			"enable_waste_tracking": kwargs.get("enable_waste_tracking", True),
			"auto_calculate": kwargs.get("auto_calculate", True),
			"calculation_frequency": kwargs.get("calculation_frequency", "Daily")
		})
	
	settings.save(ignore_permissions=True)
	return settings.name
