# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class IntegratedModules(Document):
	def validate(self):
		"""Validate integrated modules configuration"""
		if not self.module_name:
			frappe.throw(_("Module name is required"))
		
		if self.enable_tracking and not any([
			self.enable_carbon_tracking,
			self.enable_energy_tracking,
			self.enable_waste_tracking
		]):
			frappe.throw(_("At least one tracking type must be enabled when tracking is enabled"))
