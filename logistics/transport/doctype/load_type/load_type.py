# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class LoadType(Document):
	def validate(self):
		"""Validate consolidation rules"""
		self.validate_consolidation_settings()
		self.validate_numeric_fields()
	
	def validate_consolidation_settings(self):
		"""Validate that when can_be_consolidated is checked, at least one consolidation constraint is set"""
		if not self.can_be_consolidated:
			return
		
		# Check if at least one consolidation constraint is set
		has_max_jobs = self.max_consolidation_jobs and self.max_consolidation_jobs > 0
		has_max_weight = self.max_weight and flt(self.max_weight) > 0
		has_max_volume = self.max_volume and flt(self.max_volume) > 0
		
		if not (has_max_jobs or has_max_weight or has_max_volume):
			frappe.msgprint(
				_("Warning: Consolidation is enabled but no limits are set. Consider setting Max Consolidation Jobs, Max Weight, or Max Volume."),
				indicator="orange"
			)
	
	def validate_numeric_fields(self):
		"""Validate that numeric fields are non-negative"""
		if self.max_consolidation_jobs and self.max_consolidation_jobs < 0:
			frappe.throw(_("Max Consolidation Jobs cannot be negative"))
		
		if self.max_weight and flt(self.max_weight) < 0:
			frappe.throw(_("Max Weight cannot be negative"))
		
		if self.max_volume and flt(self.max_volume) < 0:
			frappe.throw(_("Max Volume cannot be negative"))
