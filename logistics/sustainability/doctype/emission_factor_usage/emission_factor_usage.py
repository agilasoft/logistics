# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class EmissionFactorUsage(Document):
	def validate(self):
		"""Validate emission factor usage"""
		if not self.emission_factor:
			frappe.throw(_("Emission Factor is required"))
		
		if not self.factor_value or self.factor_value <= 0:
			frappe.throw(_("Factor value must be positive"))
