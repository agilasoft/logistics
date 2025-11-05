# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class EnergyEfficiencyMetrics(Document):
	def validate(self):
		"""Validate energy efficiency metrics"""
		if not self.metric_name:
			frappe.throw(_("Metric Name is required"))
		
		if not self.efficiency_value or self.efficiency_value < 0:
			frappe.throw(_("Efficiency Value must be non-negative"))
