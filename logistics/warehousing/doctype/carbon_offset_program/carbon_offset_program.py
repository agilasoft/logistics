# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class CarbonOffsetProgram(Document):
	def before_save(self):
		"""Calculate total cost before saving"""
		self.calculate_total_cost()
	
	def calculate_total_cost(self):
		"""Calculate total cost from offset quantity and cost per unit"""
		if self.offset_quantity and self.cost_per_unit:
			self.total_cost = flt(self.offset_quantity) * flt(self.cost_per_unit)
		else:
			self.total_cost = 0
	
	def get_offset_effectiveness(self):
		"""Get offset effectiveness score based on verification status"""
		effectiveness_scores = {
			"Certified": 100,
			"Third-Party Verified": 85,
			"Self-Reported": 60,
			"Not Verified": 30
		}
		return effectiveness_scores.get(self.verification_status, 30)
