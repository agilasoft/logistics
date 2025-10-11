# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate


class CarbonReductionTarget(Document):
	def before_save(self):
		"""Calculate reduction percentage before saving"""
		self.calculate_reduction_percentage()
		self.update_status()
	
	def calculate_reduction_percentage(self):
		"""Calculate reduction percentage from baseline and target values"""
		if self.baseline_value and self.target_value:
			if self.baseline_value > 0:
				reduction = ((flt(self.baseline_value) - flt(self.target_value)) / flt(self.baseline_value)) * 100
				self.reduction_percentage = max(reduction, 0)  # Only positive reductions
			else:
				self.reduction_percentage = 0
		else:
			self.reduction_percentage = 0
	
	def update_status(self):
		"""Update status based on target date and progress"""
		if not self.target_date:
			return
		
		today = getdate()
		target_date = getdate(self.target_date)
		
		if today > target_date:
			if self.status == "In Progress":
				self.status = "Behind Schedule"
		elif today <= target_date and self.status == "Not Started":
			self.status = "In Progress"
