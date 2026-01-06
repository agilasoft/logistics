# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt
from logistics.warehousing.api_parts.billing_methods import get_billing_quantity


class PeriodicBillingCharges(Document):
	def before_save(self):
		"""Automatically compute billing quantities for storage charges only"""
		# Only compute for storage charges, not for charges from warehouse jobs
		if self.warehouse_job:
			# This is a charge from warehouse job, don't recompute
			return
		
		self._compute_storage_quantities()
	
	def _compute_storage_quantities(self):
		"""Compute billing quantities for storage charges only"""
		if not self.billing_method or not self.parent or not self.handling_unit:
			return
		
		try:
			# Get parent document context
			parent_doc = frappe.get_doc(self.parenttype, self.parent)
			
			# Only compute for storage context
			context = "storage"
			
			# Get billing quantity based on method
			billing_quantity = get_billing_quantity(
				context=context,
				billing_method=self.billing_method,
				reference_doc=self.handling_unit,
				date_from=getattr(parent_doc, 'date_from', None),
				date_to=getattr(parent_doc, 'date_to', None)
			)
			
			if billing_quantity > 0:
				# Update quantity
				self.quantity = billing_quantity
				
				# Update method-specific quantities for storage
				if self.billing_method == "Per Volume":
					self.volume_quantity = billing_quantity
					self.volume_uom = self.volume_uom or "CBM"
				elif self.billing_method == "Per Weight":
					self.weight_quantity = billing_quantity
					self.weight_uom = self.weight_uom or "Kg"
				elif self.billing_method == "Per Handling Unit":
					self.handling_unit_quantity = billing_quantity
					self.handling_unit_uom = self.handling_unit_uom or "Nos"
				elif self.billing_method == "High Water Mark":
					self.peak_quantity = billing_quantity
					self.peak_uom = self.peak_uom or "CBM"
				
				# Recalculate total
				self.total = flt(self.quantity) * flt(self.rate or 0)
				
		except Exception as e:
			frappe.log_error(f"Error computing storage quantities for {self.name}: {str(e)}")
