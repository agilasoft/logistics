# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


class CASSSettlementPeriod(Document):
	def before_insert(self):
		if not self.naming_series:
			self.naming_series = "CASSP-.YYYY.-.#####"
		self._apply_settings_defaults()

	def validate(self):
		self._apply_settings_defaults()
		if self.period_start and self.period_end and getdate(self.period_end) < getdate(self.period_start):
			frappe.throw(_("Period End cannot be before Period Start"))

	def _apply_settings_defaults(self):
		if self.participant_code and self.cass_country:
			return
		from logistics.air_freight.utils.iata_settings_utils import get_settings

		settings = get_settings(company=self.company)
		if not settings:
			return
		if not self.participant_code:
			self.participant_code = settings.cass_participant_code
		if not self.cass_country:
			self.cass_country = getattr(settings, "cass_country", None)

	def recompute_totals(self):
		files = frappe.get_all(
			"CASS File",
			filters={"settlement_period": self.name},
			pluck="name",
		)
		total = 0.0
		matched_amt = 0.0
		line_count = 0
		unmatched = 0
		invoiced = 0
		for name in files:
			doc = frappe.get_doc("CASS File", name)
			for row in doc.billing_lines or []:
				line_count += 1
				amount = flt(row.amount)
				total += amount
				if row.match_status == "Unmatched":
					unmatched += 1
				else:
					matched_amt += amount
				if row.match_status == "Invoiced" or row.purchase_invoice:
					invoiced += 1
		self.total_amount = total
		self.matched_amount = matched_amt
		self.line_count = line_count
		self.unmatched_count = unmatched
		self.invoiced_count = invoiced
		if self.status == "Closed":
			return
		if invoiced and invoiced == line_count and line_count:
			self.status = "Invoiced"
		elif line_count and unmatched == 0:
			self.status = "Matched"
		elif line_count:
			self.status = "Imported"

	@frappe.whitelist()
	def create_draft_purchase_invoices(self):
		from logistics.air_freight.casslink.invoice import create_draft_purchase_invoices

		return create_draft_purchase_invoices(self.name)
