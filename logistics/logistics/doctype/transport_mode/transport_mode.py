# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class TransportMode(Document):
	def validate(self):
		if not self.default_transport_document_type:
			return
		mode_key = self.name or self.mode_code
		if not mode_key:
			return
		doc = frappe.get_doc("Transport Document Type", self.default_transport_document_type)
		allowed = {r.transport_mode for r in (doc.transport_modes or [])}
		if mode_key not in allowed:
			frappe.throw(
				_(
					"Transport Document Type {0} is not allowed for Transport Mode {1}. Add this mode on that document type or pick another default."
				).format(frappe.bold(self.default_transport_document_type), frappe.bold(mode_key))
			)
