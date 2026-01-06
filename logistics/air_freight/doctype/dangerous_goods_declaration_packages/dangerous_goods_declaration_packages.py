# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class DangerousGoodsDeclarationPackages(Document):
	def validate(self):
		"""Validate dangerous goods declaration package"""
		self.validate_required_fields()
		self.validate_radioactive_materials()
		self.validate_temperature_controlled()
	
	def validate_required_fields(self):
		"""Validate required fields for dangerous goods package"""
		if not self.un_number:
			frappe.throw(_("UN Number is required for dangerous goods package"))
		
		if not self.proper_shipping_name:
			frappe.throw(_("Proper Shipping Name is required for dangerous goods package"))
		
		if not self.dg_class:
			frappe.throw(_("DG Class is required for dangerous goods package"))
		
		if not self.emergency_contact:
			frappe.throw(_("Emergency contact is required for dangerous goods package"))
		
		if not self.emergency_phone:
			frappe.throw(_("Emergency phone is required for dangerous goods package"))
	
	def validate_radioactive_materials(self):
		"""Validate radioactive materials requirements"""
		if self.is_radioactive:
			if not self.net_quantity:
				frappe.throw(_("Net quantity is required for radioactive materials"))
	
	def validate_temperature_controlled(self):
		"""Validate temperature controlled materials requirements"""
		if self.temp_controlled:
			if not self.min_temperature and not self.max_temperature:
				frappe.throw(_("Temperature range is required for temperature controlled materials"))
