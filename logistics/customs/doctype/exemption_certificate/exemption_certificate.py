# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, getdate, nowdate


class ExemptionCertificate(Document):
	def validate(self):
		"""Validate exemption certificate data"""
		if self.valid_from and self.valid_to:
			if getdate(self.valid_from) > getdate(self.valid_to):
				frappe.throw(_("Valid From date cannot be after Valid To date."))
		
		if self.exemption_value and self.exemption_value < 0:
			frappe.throw(_("Exemption Value cannot be negative."))
		
		if self.exemption_quantity and self.exemption_quantity < 0:
			frappe.throw(_("Exemption Quantity cannot be negative."))
	
	def before_save(self):
		"""Calculate remaining values and update status"""
		self.calculate_remaining()
		self.update_status()
		self.update_verification_date()
	
	def calculate_remaining(self):
		"""Calculate remaining value and quantity"""
		exemption_value = flt(self.exemption_value or 0)
		exemption_quantity = flt(self.exemption_quantity or 0)
		used_value = flt(self.used_value or 0)
		used_quantity = flt(self.used_quantity or 0)
		
		self.remaining_value = exemption_value - used_value
		self.remaining_quantity = exemption_quantity - used_quantity
		
		# Ensure remaining values are not negative
		if self.remaining_value < 0:
			self.remaining_value = 0
		if self.remaining_quantity < 0:
			self.remaining_quantity = 0
	
	def update_status(self):
		"""Update status based on validity and remaining values"""
		if self.status == "Active":
			# Check if expired
			if self.valid_to and getdate(self.valid_to) < nowdate():
				self.status = "Expired"
			# Check if fully used
			elif self.exemption_value and self.remaining_value <= 0:
				if self.exemption_quantity and self.remaining_quantity <= 0:
					self.status = "Expired"
	
	def update_verification_date(self):
		"""Update verification date when verified"""
		if self.verification_status == "Verified" and not self.verification_date:
			self.verification_date = nowdate()
			if not self.verified_by:
				self.verified_by = frappe.session.user

