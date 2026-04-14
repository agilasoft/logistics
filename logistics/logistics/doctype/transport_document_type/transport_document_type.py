# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class TransportDocumentType(Document):
	def validate(self):
		if not self.transport_modes:
			frappe.throw(_("Select at least one Transport Mode."))
