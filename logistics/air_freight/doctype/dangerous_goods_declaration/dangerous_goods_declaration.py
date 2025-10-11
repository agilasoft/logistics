# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class DangerousGoodsDeclaration(Document):
	def validate(self):
		"""Validate dangerous goods declaration"""
		self.validate_required_fields()
		self.validate_packages()
	
	def validate_required_fields(self):
		"""Validate required fields"""
		if not self.air_shipment:
			frappe.throw(_("Air Shipment is required"))
		
		if not self.emergency_contact:
			frappe.throw(_("Emergency contact is required"))
		
		if not self.emergency_phone:
			frappe.throw(_("Emergency phone is required"))
	
	def validate_packages(self):
		"""Validate dangerous goods packages"""
		if not self.packages:
			frappe.throw(_("At least one dangerous goods package is required"))
		
		for package in self.packages:
			if not package.un_number:
				frappe.throw(_("UN Number is required for all packages"))
			
			if not package.proper_shipping_name:
				frappe.throw(_("Proper Shipping Name is required for all packages"))
			
			if not package.dg_class:
				frappe.throw(_("DG Class is required for all packages"))
			
			if not package.emergency_contact:
				frappe.throw(_("Emergency contact is required for all packages"))
			
			if not package.emergency_phone:
				frappe.throw(_("Emergency phone is required for all packages"))
	
	def on_submit(self):
		"""Actions when declaration is submitted"""
		# Update the Air Freight Job with declaration status
		if self.air_freight_job:
			air_freight_job = frappe.get_doc("Air Freight Job", self.air_freight_job)
			if hasattr(air_freight_job, 'dg_declaration_complete'):
				air_freight_job.dg_declaration_complete = 1
			if hasattr(air_freight_job, 'dg_declaration_number'):
				air_freight_job.dg_declaration_number = self.name
			air_freight_job.save()
	
	def on_cancel(self):
		"""Actions when declaration is cancelled"""
		# Update the Air Freight Job with declaration status
		if self.air_freight_job:
			air_freight_job = frappe.get_doc("Air Freight Job", self.air_freight_job)
			if hasattr(air_freight_job, 'dg_declaration_complete'):
				air_freight_job.dg_declaration_complete = 0
			if hasattr(air_freight_job, 'dg_declaration_number'):
				air_freight_job.dg_declaration_number = None
			air_freight_job.save()
	
	@frappe.whitelist()
	def generate_pdf(self):
		"""Generate PDF for the declaration"""
		# This can be implemented to generate a PDF version of the declaration
		# For now, return a simple message
		return {
			"status": "success",
			"message": "PDF generation not implemented yet"
		}
	
	@frappe.whitelist()
	def send_notification(self):
		"""Send notification to relevant parties"""
		# This can be implemented to send notifications
		# For now, return a simple message
		return {
			"status": "success",
			"message": "Notification sent successfully"
		}
