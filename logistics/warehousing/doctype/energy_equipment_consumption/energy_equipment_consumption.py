# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class EnergyEquipmentConsumption(Document):
	def before_save(self):
		"""Calculate energy per hour before saving"""
		self.calculate_energy_per_hour()
	
	def calculate_energy_per_hour(self):
		"""Calculate energy consumption per hour"""
		if self.consumption_value and self.operating_hours and self.operating_hours > 0:
			self.energy_per_hour = flt(self.consumption_value) / flt(self.operating_hours)
		else:
			self.energy_per_hour = 0
	
	def get_efficiency_score(self):
		"""Get efficiency score based on rating"""
		efficiency_scores = {
			"A+++": 100,
			"A++": 95,
			"A+": 90,
			"A": 85,
			"B": 75,
			"C": 65,
			"D": 55,
			"E": 45,
			"F": 35,
			"G": 25
		}
		return efficiency_scores.get(self.efficiency_rating, 50)
