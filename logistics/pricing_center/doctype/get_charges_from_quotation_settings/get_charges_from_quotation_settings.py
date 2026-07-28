# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class GetChargesfromQuotationSettings(Document):
	def validate(self):
		from logistics.utils.get_charges_from_quotation import (
			GCFQ_FILTER_CATALOG,
			seed_gcfq_filter_settings_rows,
		)

		if not self.filter_settings:
			seed_gcfq_filter_settings_rows(self)
			return

		seen: set[tuple[str, str]] = set()
		for row in self.filter_settings:
			job = (row.job_doctype or "").strip()
			key = (row.filter_key or "").strip()
			if not job or not key:
				frappe.throw(_("Job DocType and Filter Key are required on every row."))
			allowed = {e["key"] for e in GCFQ_FILTER_CATALOG.get(job, ())}
			if key not in allowed:
				frappe.throw(
					_("Filter Key {0} is not valid for {1}.").format(key, job),
					title=_("Invalid Filter Key"),
				)
			pair = (job, key)
			if pair in seen:
				frappe.throw(
					_("Duplicate filter setting for {0} / {1}.").format(job, key),
					title=_("Duplicate Filter"),
				)
			seen.add(pair)
			row.enabled = 1 if cint(row.enabled) else 0
			row.editable = 1 if cint(row.editable) else 0
