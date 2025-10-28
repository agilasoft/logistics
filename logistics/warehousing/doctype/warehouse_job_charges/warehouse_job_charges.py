# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt
from frappe import _
from logistics.warehousing.api_parts.billing_methods import get_billing_quantity


class WarehouseJobCharges(Document):
	def before_save(self):
		"""Automatically compute billing quantities based on billing method"""
		self._compute_billing_quantities()
		# Standard cost calculation is now handled by Calculate Charges workflow
	
	def _compute_billing_quantities(self):
		"""Compute billing quantities based on the billing method"""
		if not self.billing_method or not self.parent:
			return
		
		try:
			# Get parent document context
			parent_doc = frappe.get_doc(self.parenttype, self.parent)
			context = self._get_charge_context(parent_doc)
			
			# Get billing quantity based on method
			billing_quantity = get_billing_quantity(
				context=context,
				billing_method=self.billing_method,
				reference_doc=self.parent,
				date_from=getattr(parent_doc, 'date_from', None),
				date_to=getattr(parent_doc, 'date_to', None)
			)
			
			if billing_quantity > 0:
				# Update quantity
				self.quantity = billing_quantity
				
				# Update method-specific quantities
				if self.billing_method == "Per Volume":
					self.volume_quantity = billing_quantity
					self.volume_uom = self.volume_uom or "CBM"
				elif self.billing_method == "Per Weight":
					self.weight_quantity = billing_quantity
					self.weight_uom = self.weight_uom or "Kg"
				elif self.billing_method == "Per Piece":
					self.piece_quantity = billing_quantity
					self.piece_uom = self.piece_uom or "Nos"
				elif self.billing_method == "Per Container":
					self.container_quantity = billing_quantity
					self.container_uom = self.container_uom or "Nos"
				elif self.billing_method == "Per Hour":
					self.hour_quantity = billing_quantity
					self.hour_uom = self.hour_uom or "Hours"
				elif self.billing_method == "Per Handling Unit":
					self.handling_unit_quantity = billing_quantity
					self.handling_unit_uom = self.handling_unit_uom or "Nos"
				elif self.billing_method == "High Water Mark":
					self.peak_quantity = billing_quantity
					self.peak_uom = self.peak_uom or "CBM"
				
				# Recalculate total
				self.total = flt(self.quantity) * flt(self.rate or 0)
				
		except Exception as e:
			frappe.log_error(f"Error computing billing quantities for {self.name}: {str(e)}")
	
	def _get_charge_context(self, parent_doc):
		"""Determine the charge context from parent document"""
		if hasattr(parent_doc, 'order_type'):
			return parent_doc.order_type.lower()
		elif hasattr(parent_doc, 'job_type'):
			return parent_doc.job_type.lower()
		else:
			return "storage"
	


def _find_customer_contract(customer):
	"""Find warehouse contract for customer"""
	if not customer:
		return None
	
	contracts = frappe.get_all(
		"Warehouse Contract",
		filters={
			"customer": customer,
			"status": "Active"
		},
		fields=["name"],
		order_by="creation desc",
		limit=1
	)
	
	return contracts[0]["name"] if contracts else None
