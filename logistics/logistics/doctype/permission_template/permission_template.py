# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from logistics.permissions.studio_logic import clean, duplicate_values, palette_color, value_key


class PermissionTemplate(Document):
	def validate(self):
		self.template_name = clean(self.template_name)
		self.description = clean(self.description)
		self.category = clean(self.category)
		if not clean(self.color):
			self.color = palette_color(self.template_name)
		duplicates = duplicate_values(
			[
				{
					"allow": row.allow,
					"for_value": row.for_value,
					"applicable_for": row.applicable_for,
				}
				for row in self.permitted_values
			]
		)
		if duplicates:
			frappe.throw(_("Duplicate permitted values on this template."))
		seen = set()
		for row in list(self.permitted_values):
			if not row.allow or not row.for_value:
				self.remove(row)
				continue
			if not frappe.db.exists("DocType", row.allow):
				frappe.throw(_("Document type {0} does not exist.").format(row.allow))
			if not frappe.db.exists(row.allow, row.for_value):
				frappe.throw(_("{0} {1} does not exist.").format(row.allow, row.for_value))
			if row.applicable_for and not frappe.db.exists("DocType", row.applicable_for):
				frappe.throw(_("Applicable For {0} does not exist.").format(row.applicable_for))
			key = value_key(
				{"allow": row.allow, "for_value": row.for_value, "applicable_for": row.applicable_for}
			)
			if key in seen:
				self.remove(row)
				continue
			seen.add(key)
