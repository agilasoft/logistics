# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class CarbonEmissionBreakdown(Document):
	def validate(self):
		"""Validate carbon emission breakdown"""
		if not self.source_type:
			frappe.throw(_("Source Type is required"))
		
		if not self.activity_data or self.activity_data <= 0:
			frappe.throw(_("Activity Data must be positive"))
		
		if not self.emissions or self.emissions < 0:
			frappe.throw(_("Emissions cannot be negative"))
