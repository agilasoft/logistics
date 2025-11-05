# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class DefaultEmissionFactors(Document):
	def validate(self):
		"""Validate default emission factors"""
		if not self.factor_name:
			frappe.throw(_("Factor name is required"))
		
		if not self.factor_value or self.factor_value <= 0:
			frappe.throw(_("Factor value must be positive"))
