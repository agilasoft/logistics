# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document


class ReturnedBilling(Document):
	def validate(self):
		if self.resolution_status in ("Resubmitted", "Cancelled", "Written Off") and not self.resolved_on:
			frappe.throw(_("Resolved On is required when Resolution Status is {0}.").format(self.resolution_status))

	def before_insert(self):
		self._refresh_dimensions_from_job()

	def before_save(self):
		self._refresh_dimensions_from_job()

	def _refresh_dimensions_from_job(self):
		if not self.job_no:
			return
		try:
			doc = frappe.db.get_value(
				"Job Number",
				self.job_no,
				["company", "branch", "cost_center", "profit_center"],
				as_dict=True,
			)
		except Exception:
			doc = None
		if not doc:
			return
		if not self.company:
			self.company = doc.company
		if not self.branch:
			self.branch = doc.branch
		if not self.cost_center:
			self.cost_center = doc.cost_center
		if not self.profit_center:
			self.profit_center = doc.profit_center
