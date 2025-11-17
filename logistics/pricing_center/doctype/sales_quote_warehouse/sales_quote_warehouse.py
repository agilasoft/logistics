# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class SalesQuoteWarehouse(Document):
	def calculate_estimated_revenue(self):
		"""Calculate estimated revenue based on calculation method"""
		if not self.calculation_method or not self.unit_rate:
			self.estimated_revenue = 0
			return
		
		try:
			quantity = flt(self.quantity) or 0
			rate = flt(self.unit_rate) or 0
			
			if self.calculation_method == "Per Unit":
				base_amount = rate * quantity
				# Apply minimum/maximum charge
				if self.minimum_charge and base_amount < flt(self.minimum_charge):
					base_amount = flt(self.minimum_charge)
				if self.maximum_charge and base_amount > flt(self.maximum_charge):
					base_amount = flt(self.maximum_charge)
				self.estimated_revenue = base_amount
				
			elif self.calculation_method == "Fixed Amount":
				self.estimated_revenue = rate
				
			elif self.calculation_method == "Base Plus Additional":
				base = flt(self.base_amount) or 0
				additional = rate * max(0, quantity - 1)
				self.estimated_revenue = base + additional
				
			elif self.calculation_method == "First Plus Additional":
				min_qty = flt(self.minimum_quantity) or 1
				if quantity <= min_qty:
					self.estimated_revenue = rate
				else:
					additional = rate * (quantity - min_qty)
					self.estimated_revenue = rate + additional
					
			elif self.calculation_method == "Percentage":
				# Percentage calculation requires base value from parent
				# For now, use rate as percentage of quantity
				self.estimated_revenue = (rate / 100) * quantity
			else:
				self.estimated_revenue = 0
				
		except Exception as e:
			frappe.log_error(f"Error calculating estimated revenue: {str(e)}", "Sales Quote Warehouse - Revenue Calculation")
			self.estimated_revenue = 0
