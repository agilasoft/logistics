# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from logistics.customs.child_row_virtual_mixin import ExemptionCertificateVirtualMixin


class DeclarationOrderExemption(Document, ExemptionCertificateVirtualMixin):
	def validate(self):
		if self.exemption_certificate:
			cert = frappe.get_doc("Exemption Certificate", self.exemption_certificate)
			if cert.status != "Active":
				frappe.throw(_("Exemption Certificate {0} is not active.").format(self.exemption_certificate))

			if cert.verification_status == "Verified":
				self.certificate_verified = 1
				if not self.verification_date:
					from frappe.utils import nowdate

					self.verification_date = nowdate()
