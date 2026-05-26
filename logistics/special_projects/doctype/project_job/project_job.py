# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ProjectJob(Document):
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

	def on_submit(self):
		try:
			from logistics.special_projects.special_project_site_materials import (
				post_site_receipts_from_project_doc,
			)

			post_site_receipts_from_project_doc(self)
		except Exception:
			frappe.log_error(
				frappe.get_traceback(),
				f"Project Job {self.name}: site materials receipt post",
			)

	def on_cancel(self):
		try:
			from logistics.special_projects.special_project_site_materials import (
				cancel_receipts_for_project_doc,
			)

			cancel_receipts_for_project_doc(self)
		except Exception:
			frappe.log_error(
				frappe.get_traceback(),
				f"Project Job {self.name}: site materials receipt cancel",
			)
