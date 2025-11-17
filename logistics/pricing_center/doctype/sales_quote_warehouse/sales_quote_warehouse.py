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
			# For warehouse quotes, quantity is calculated from actual jobs, so use default of 1 for estimation
			quantity = 1.0
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
				# Percentage calculation - use rate as percentage
				self.estimated_revenue = (rate / 100) * quantity
			else:
				self.estimated_revenue = 0
				
		except Exception as e:
			frappe.log_error(f"Error calculating estimated revenue: {str(e)}", "Sales Quote Warehouse - Revenue Calculation")
			self.estimated_revenue = 0


@frappe.whitelist()
def calculate_estimated_revenue_for_row(doc):
	"""Calculate estimated revenue for a row - called from client side"""
	try:
		from frappe.model import get_doc
		row_doc = frappe._dict(doc)
		
		calculation_method = row_doc.get("calculation_method")
		unit_rate = flt(row_doc.get("unit_rate") or 0)
		
		if not calculation_method or not unit_rate:
			return {"estimated_revenue": 0}
		
		# For warehouse quotes, quantity is calculated from actual jobs, so use default of 1 for estimation
		quantity = 1.0
		
		if calculation_method == "Per Unit":
			base_amount = unit_rate * quantity
			# Apply minimum/maximum charge
			minimum_charge = flt(row_doc.get("minimum_charge") or 0)
			maximum_charge = flt(row_doc.get("maximum_charge") or 0)
			if minimum_charge > 0 and base_amount < minimum_charge:
				base_amount = minimum_charge
			if maximum_charge > 0 and base_amount > maximum_charge:
				base_amount = maximum_charge
			return {"estimated_revenue": base_amount}
			
		elif calculation_method == "Fixed Amount":
			return {"estimated_revenue": unit_rate}
			
		elif calculation_method == "Base Plus Additional":
			base = flt(row_doc.get("base_amount") or 0)
			additional = unit_rate * max(0, quantity - 1)
			return {"estimated_revenue": base + additional}
			
		elif calculation_method == "First Plus Additional":
			min_qty = flt(row_doc.get("minimum_quantity") or 1)
			if quantity <= min_qty:
				return {"estimated_revenue": unit_rate}
			else:
				additional = unit_rate * (quantity - min_qty)
				return {"estimated_revenue": unit_rate + additional}
				
		elif calculation_method == "Percentage":
			return {"estimated_revenue": (unit_rate / 100) * quantity}
		else:
			return {"estimated_revenue": 0}
			
	except Exception as e:
		frappe.log_error(f"Error calculating estimated revenue: {str(e)}", "Sales Quote Warehouse - Revenue Calculation")
		return {"estimated_revenue": 0}
