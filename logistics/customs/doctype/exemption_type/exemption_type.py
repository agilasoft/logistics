# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class ExemptionType(Document):
	def validate(self):
		"""Validate exemption type data"""
		if self.valid_from and self.valid_to:
			from frappe.utils import getdate
			if getdate(self.valid_from) > getdate(self.valid_to):
				frappe.throw(_("Valid From date cannot be after Valid To date."))
		
		if self.exemption_percentage and (self.exemption_percentage < 0 or self.exemption_percentage > 100):
			frappe.throw(_("Exemption Percentage must be between 0 and 100."))
		
		if self.maximum_value and self.maximum_value < 0:
			frappe.throw(_("Maximum Value cannot be negative."))
		
		if self.maximum_quantity and self.maximum_quantity < 0:
			frappe.throw(_("Maximum Quantity cannot be negative."))
		
		if self.requires_certificate and not self.certificate_type:
			frappe.throw(_("Certificate Type is required when Requires Certificate is checked."))

