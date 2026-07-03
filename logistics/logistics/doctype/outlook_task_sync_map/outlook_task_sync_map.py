# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class OutlookTaskSyncMap(Document):
	def before_insert(self):
		self._ensure_unique_task_user()

	def validate(self):
		self._ensure_unique_task_user()

	def _ensure_unique_task_user(self):
		if not self.task or not self.user:
			return
		existing = frappe.db.exists(
			"Outlook Task Sync Map",
			{"task": self.task, "user": self.user, "name": ("!=", self.name)},
		)
		if existing:
			frappe.throw(
				frappe._("A sync map already exists for task {0} and user {1}").format(
					self.task, self.user
				)
			)
