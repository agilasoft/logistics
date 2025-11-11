# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class PermitType(Document):
	def validate(self):
		"""Validate permit type data"""
		if self.renewal_required and not self.renewal_period_days:
			frappe.throw(_("Renewal Period (Days) is required when Renewal Required is checked."))
		
		if self.validity_period and self.validity_period <= 0:
			frappe.throw(_("Validity Period must be greater than 0."))
		
		if self.processing_time_days and self.processing_time_days < 0:
			frappe.throw(_("Processing Time cannot be negative."))

