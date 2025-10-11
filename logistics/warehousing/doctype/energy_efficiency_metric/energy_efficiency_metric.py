# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class EnergyEfficiencyMetric(Document):
	def before_save(self):
		"""Calculate improvement percentage before saving"""
		self.calculate_improvement_percentage()
	
	def calculate_improvement_percentage(self):
		"""Calculate improvement percentage based on target vs actual"""
		if self.efficiency_value and self.target_value:
			if self.efficiency_value > 0:
				improvement = ((flt(self.target_value) - flt(self.efficiency_value)) / flt(self.efficiency_value)) * 100
				self.improvement_percentage = max(improvement, 0)  # Only positive improvements
			else:
				self.improvement_percentage = 0
		else:
			self.improvement_percentage = 0
