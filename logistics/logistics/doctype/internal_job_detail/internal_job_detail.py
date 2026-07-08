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
	"""Thin child row: pointer to an Internal Job document.

	Parameter fields are ``fetch_from`` views of the linked ``Internal Job``; the source of truth is
	the Internal Job record. The parent booking's ``before_save`` (see
	``logistics.utils.internal_job_persistence``) reconciles edits in either direction.
	"""

	def get_invalid_links(self, is_submittable=False):
		invalid_links, cancelled_links = super().get_invalid_links(is_submittable=is_submittable)
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
			jn = (getattr(self, "job_no", None) or "").strip()
			if jt in ("Inbound Order", "Release Order", "Transfer Order") and jn:
				return
			self.job_type = "VAS Order"
			return
		self.job_type = expected
