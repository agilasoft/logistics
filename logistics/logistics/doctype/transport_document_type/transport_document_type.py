# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class TransportDocumentType(Document):
	def validate(self):
		rows = self.get("transport_modes") or []
		if not any(getattr(r, "transport_mode", None) for r in rows):
			frappe.throw(_("Select at least one Transport Mode."))
