# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import today, getdate, nowdate


class PermitApplication(Document):
	def validate(self):
		"""Validate permit application data"""
		if self.valid_from and self.valid_to:
			if getdate(self.valid_from) > getdate(self.valid_to):
				frappe.throw(_("Valid From date cannot be after Valid To date."))
		
		if self.renewal_of:
			renewal_doc = frappe.get_doc("Permit Application", self.renewal_of)
			if renewal_doc.status not in ["Approved", "Expired"]:
				frappe.throw(_("Can only renew an Approved or Expired permit."))
	
	def before_save(self):
		"""Auto-update dates based on status"""
		self.update_status_dates()
		self.set_default_currency()
	
	def update_status_dates(self):
		"""Update approval/rejection dates based on status"""
		from frappe.utils import nowdate
		
		if self.status == "Approved" and not self.approval_date:
			self.approval_date = nowdate()
		elif self.status == "Rejected" and not self.rejection_date:
			self.rejection_date = nowdate()
	
	def set_default_currency(self):
		"""Set default currency from company if not set"""
		if self.company and not self.currency:
			company_doc = frappe.get_doc("Company", self.company)
			if company_doc.default_currency:
				self.currency = company_doc.default_currency
	
	def on_update(self):
		"""Handle status changes"""
		if self.status == "Approved" and self.permit_type:
			# Auto-set validity dates from permit type if not set
			permit_type = frappe.get_doc("Permit Type", self.permit_type)
			if permit_type.validity_period and not self.valid_to:
				from frappe.utils import add_days
				if self.valid_from:
					self.valid_to = add_days(self.valid_from, permit_type.validity_period)
				elif self.approval_date:
					self.valid_from = self.approval_date
					self.valid_to = add_days(self.approval_date, permit_type.validity_period)

