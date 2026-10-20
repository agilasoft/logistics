# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class PermissionStudioSettings(Document):
	def validate(self):
		if int(self.list_page_size or 0) < 1:
			frappe.throw(_("List page size must be at least 1."))
		if int(self.picker_page_size or 0) < 1:
			frappe.throw(_("Document list size must be at least 1."))
