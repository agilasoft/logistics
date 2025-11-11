# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class DeclarationExemption(Document):
	def validate(self):
		"""Validate declaration exemption"""
		if self.exemption_certificate:
			# Validate certificate is active and not expired
			cert = frappe.get_doc("Exemption Certificate", self.exemption_certificate)
			if cert.status != "Active":
				frappe.throw(_("Exemption Certificate {0} is not active.").format(self.exemption_certificate))
			
			# Set certificate number if not set
			if not self.certificate_number:
				self.certificate_number = cert.certificate_number
			
			# Set certificate verified status
			if cert.verification_status == "Verified":
				self.certificate_verified = 1
				if not self.verification_date:
					from frappe.utils import nowdate
					self.verification_date = nowdate()

