# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class SustainabilityAdditionalMetrics(Document):
	def validate(self):
		"""Validate sustainability additional metrics"""
		if not self.key:
			frappe.throw(_("Key is required"))
		
		if not self.value:
			frappe.throw(_("Value is required"))
