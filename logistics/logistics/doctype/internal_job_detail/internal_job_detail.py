# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json

import frappe
from frappe.model.document import Document

from logistics.utils.charge_service_type import default_job_type_for_internal_job_service_type


@frappe.whitelist()
def suggest_job_description(row):
	"""Build Job Description text from service-type parameters (used by Internal Job Detail client script)."""
	if isinstance(row, str):
		row = json.loads(row)
	if not row:
		return ""
	from logistics.utils.internal_job_detail_description import build_internal_job_description

	return build_internal_job_description(row) or ""


class InternalJobDetail(Document):
	"""Child row: internal job link + service parameters (aligned with Sales Quote Charge)."""

	def get_invalid_links(self, is_submittable=False):
		invalid_links, cancelled_links = super().get_invalid_links(is_submittable=is_submittable)
		# job_no is a historical pointer; linked operational docs may be cancelled while parent still saves.
		cancelled_links = [c for c in cancelled_links if c[0] != "job_no"]
		return invalid_links, cancelled_links

	def validate(self):
		st = (self.service_type or "").strip()
		if not st:
			return
		expected = default_job_type_for_internal_job_service_type(st)
		if not expected:
			return
		jt = (self.job_type or "").strip()
		if st == "Warehousing":
			if jt in ("Inbound Order", "Release Order", "Transfer Order"):
				return
			self.job_type = "Inbound Order"
			return
		self.job_type = expected
