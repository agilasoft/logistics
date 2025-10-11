# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class CarbonEmissionBreakdown(Document):
	def before_save(self):
		"""Calculate emission value and percentage before saving"""
		self.calculate_emission_value()
		self.calculate_percentage_of_total()
	
	def calculate_emission_value(self):
		"""Calculate emission value from activity data and emission factor"""
		if self.activity_data and self.emission_factor:
			self.emission_value = flt(self.activity_data) * flt(self.emission_factor)
		else:
			self.emission_value = 0
	
	def calculate_percentage_of_total(self):
		"""Calculate percentage of total emissions"""
		# This will be calculated by the parent document
		# as it needs access to total emissions
		pass
