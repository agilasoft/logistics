# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class GatePassItem(Document):
	def validate(self):
		"""Validate gate pass item data"""
		self.validate_item_details()
		self.validate_quantity()
	
	def validate_item_details(self):
		"""Validate item details"""
		if self.item_code:
			item = frappe.get_doc("Warehouse Item", self.item_code)
			if not self.item_name:
				self.item_name = item.item_name
			if not self.description:
				self.description = item.description
			if not self.uom:
				self.uom = item.uom
	
	def validate_quantity(self):
		"""Validate quantity"""
		if self.qty and self.qty <= 0:
			frappe.throw("Quantity must be greater than 0")

