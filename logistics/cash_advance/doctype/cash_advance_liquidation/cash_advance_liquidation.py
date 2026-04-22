# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from logistics.cash_advance.accounting import (
	_validate_cash_bank_account,
	cancel_journal_entry,
	create_liquidation_journal_entry,
	ensure_payee_for_party_accounts,
)
from logistics.cash_advance.job_charge_items import get_item_codes_for_job_number


class CashAdvanceLiquidation(Document):
	def validate(self):
		self._validate_linked_request()
		self._validate_items_against_job()

		if self.total_requested and self.total_requested < 0:
			frappe.throw(_("Total Requested cannot be negative"))

		self.calculate_total()

	def before_submit(self):
		self.calculate_total()
		if not self.fund_source:
			frappe.throw(_("Fund Source (Liquidation) is required to submit."))
		_validate_cash_bank_account(self.fund_source, self.company)
		ensure_payee_for_party_accounts(self)
		if not self.cash_advance_request:
			frappe.throw(_("Cash Advance Request is required."))
		if frappe.db.get_value("Cash Advance Request", self.cash_advance_request, "docstatus") != 1:
			frappe.throw(_("Cash Advance Request must be submitted before liquidation."))
		if not self.items:
			frappe.throw(_("Add at least one item before submitting."))
		tl = sum(flt(getattr(r, "amount_liquidated", 0), 2) for r in self.items)
		if tl <= 0:
			frappe.throw(_("Amount Liquidated must be greater than zero on at least one line."))

	def on_submit(self):
		if frappe.db.get_value(self.doctype, self.name, "liquidation_journal_entry"):
			return
		je_name = create_liquidation_journal_entry(self)
		frappe.db.set_value(self.doctype, self.name, "liquidation_journal_entry", je_name, update_modified=False)

	def on_cancel(self):
		cancel_journal_entry(self.liquidation_journal_entry)
		frappe.db.set_value(self.doctype, self.name, "liquidation_journal_entry", None, update_modified=False)

	def _validate_linked_request(self):
		if not self.cash_advance_request:
			return
		if not frappe.db.exists("Cash Advance Request", self.cash_advance_request):
			frappe.throw(_("Cash Advance Request {0} does not exist.").format(self.cash_advance_request))
		req_co = frappe.db.get_value("Cash Advance Request", self.cash_advance_request, "company")
		if req_co and self.company and req_co != self.company:
			frappe.throw(_("Company must match the linked Cash Advance Request."))

	def _validate_items_against_job(self):
		if not self.job_number:
			if any(getattr(r, "item_code", None) for r in self.items or []):
				frappe.throw(_("Job Number is required (load from Cash Advance Request)."))
			return

		allowed = set(get_item_codes_for_job_number(self.job_number))
		for row in self.items or []:
			if not row.item_code:
				continue
			if row.item_code not in allowed:
				frappe.throw(
					_("Charge Item {0} is not on the charges for Job Number {1}.").format(
						row.item_code, self.job_number
					)
				)

	def calculate_total(self):
		total_requested = 0
		total_liquidated = 0

		if self.items:
			for item in self.items:
				if item.amount_requested:
					total_requested += flt(item.amount_requested)
				if item.amount_liquidated:
					total_liquidated += flt(item.amount_liquidated)

		self.total_requested = total_requested
		self.total_liquidated = total_liquidated
		self.unliquidated = total_requested - total_liquidated

		return {
			"total_requested": total_requested,
			"total_liquidated": total_liquidated,
			"unliquidated": self.unliquidated,
		}
