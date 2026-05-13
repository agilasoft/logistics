# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ProjectTaskJob(Document):
	def validate(self):
		if self.special_project:
			row = frappe.db.get_value(
				"Special Project",
				self.special_project,
				["customer", "project"],
				as_dict=True,
			)
			if row:
				if row.get("customer") and not self.customer:
					self.customer = row.customer
				# project is fetch_from on the form; keep DB row aligned if user saved without child fetch
				if row.get("project") and not self.get("project"):
					self.project = row.project
