# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from logistics.job_management.job_task import JOB_TASK_PARENTS


class JobTask(Document):
	def validate(self):
		self._require_known_parent()
		self._set_job_number_from_parent()
		self._set_completion()
		self._require_unique_task_code()

	def _require_known_parent(self):
		if self.job_type and self.job_type not in JOB_TASK_PARENTS:
			frappe.throw(
				_("{0} does not use Job Tasks.").format(self.job_type),
				title=_("Job Task"),
			)

	def _set_job_number_from_parent(self):
		if self.job_number or not self.job_type or not self.job_no:
			return
		if not frappe.db.exists("DocType", self.job_type):
			return
		if not frappe.get_meta(self.job_type).has_field("job_number"):
			return
		self.job_number = frappe.db.get_value(self.job_type, self.job_no, "job_number")

	def _set_completion(self):
		if self.status != "Completed":
			return
		if not self.completed_on:
			self.completed_on = frappe.utils.now()
		if not self.completed_by:
			self.completed_by = frappe.session.user

	def _require_unique_task_code(self):
		if not self.job_type or not self.job_no or not self.task_code:
			return
		filters = {
			"job_type": self.job_type,
			"job_no": self.job_no,
			"task_code": self.task_code,
		}
		if self.name:
			filters["name"] = ["!=", self.name]
		if frappe.db.exists("Job Task", filters):
			frappe.throw(
				_("Job Task {0} already exists for {1} {2}.").format(
					self.task_code, self.job_type, self.job_no
				),
				title=_("Job Task"),
			)
