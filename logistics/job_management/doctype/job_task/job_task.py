# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class JobTask(Document):
	"""Child row on a booking or job. Same role as a milestone row."""

	def validate(self):
		if self.status != "Completed":
			return
		if not self.completed_on:
			self.completed_on = frappe.utils.now()
		if not self.completed_by:
			self.completed_by = frappe.session.user
