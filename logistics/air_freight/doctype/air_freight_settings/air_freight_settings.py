# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class AirFreightSettings(Document):
	def validate(self):
		"""Validate Air Freight Settings"""
		# Validate company is set
		if not self.company:
			frappe.throw("Company is required")
		
		# Validate volume to weight factor
		if self.volume_to_weight_factor and self.volume_to_weight_factor <= 0:
			frappe.throw("Volume to Weight Factor must be greater than 0")
		
		# Validate consolidation limits
		if self.max_consolidation_weight and self.max_consolidation_weight <= 0:
			frappe.throw("Max Consolidation Weight must be greater than 0")
		
		if self.max_consolidation_volume and self.max_consolidation_volume <= 0:
			frappe.throw("Max Consolidation Volume must be greater than 0")
		
		# Validate alert check interval
		if self.alert_check_interval_hours and self.alert_check_interval_hours <= 0:
			frappe.throw("Alert Check Interval must be greater than 0")
		
		# Validate billing check interval
		if self.billing_check_interval_hours and self.billing_check_interval_hours <= 0:
			frappe.throw("Billing Check Interval must be greater than 0")
	
	def on_update(self):
		"""Called after saving"""
		# Clear cache to ensure changes take effect
		frappe.clear_cache()
		
		# Log the update
		frappe.logger().info(f"Air Freight Settings updated for company {self.company} by {frappe.session.user}")
	
	@staticmethod
	def get_settings(company=None):
		"""Get Air Freight Settings for a company"""
		if not company:
			company = frappe.defaults.get_user_default("Company")
		
		if not company:
			return None
		
		try:
			# Get settings by company field
			settings_name = frappe.db.get_value("Air Freight Settings", {"company": company}, "name")
			if settings_name:
				return frappe.get_doc("Air Freight Settings", settings_name)
		except frappe.DoesNotExistError:
			pass
		
		return None
	
	@staticmethod
	def get_default_value(company, fieldname):
		"""Get default value for a field from Air Freight Settings"""
		try:
			settings = AirFreightSettings.get_settings(company)
			if settings:
				return getattr(settings, fieldname, None)
		except frappe.DoesNotExistError:
			pass
		
		return None

