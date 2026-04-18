# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ContainerRefundReadiness(Document):
	def validate(self):
		if self.status == "Waived" and not (self.waiver_reason or "").strip():
			frappe.throw(_("Waiver reason is required when status is Waived."), title=_("Refund readiness"))
		if self.status == "Received" and frappe.utils.cint(self.attachment_required) and not self.attach:
			frappe.throw(_("Attachment is required for this line before marking Received."), title=_("Refund readiness"))
