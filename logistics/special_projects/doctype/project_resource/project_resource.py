# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ProjectResource(Document):
	def validate(self):
		filters = {"title": self.title, "resource_category": self.resource_category}
		if self.name:
			filters["name"] = ["!=", self.name]
		if frappe.get_all("Project Resource", filters=filters, limit=1):
			frappe.throw(
				_("A Project Resource with this Resource Name and Resource Category already exists.")
			)
