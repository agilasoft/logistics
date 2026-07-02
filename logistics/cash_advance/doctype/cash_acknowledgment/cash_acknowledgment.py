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
	create_cash_acknowledgment_journal_entry,
	ensure_payee_for_party_accounts,
	get_cash_advance_settlement_summary,
)
from logistics.cash_advance.totals_sync import sync_cash_advance_request_settlement_totals


class CashAcknowledgment(Document):
	def validate(self):
		self._validate_linked_request()
		self._validate_fund_source_company()
		self._validate_settlement_amount()

	def before_submit(self):
		if not self.fund_source:
			frappe.throw(_("Fund Source is required to submit."))
		_validate_cash_bank_account(self.fund_source, self.company)
		ensure_payee_for_party_accounts(self)
		if not self.cash_advance_request:
			frappe.throw(_("Cash Advance Request is required."))
		if frappe.db.get_value("Cash Advance Request", self.cash_advance_request, "docstatus") != 1:
			frappe.throw(_("Cash Advance Request must be submitted before cash acknowledgment."))
		if flt(self.amount, 2) <= 0:
			frappe.throw(_("Amount must be greater than zero."))
		self._validate_settlement_amount()

	def on_submit(self):
		if frappe.db.get_value(self.doctype, self.name, "journal_entry"):
			return
		je_name = create_cash_acknowledgment_journal_entry(self)
		frappe.db.set_value(self.doctype, self.name, "journal_entry", je_name, update_modified=False)
		sync_cash_advance_request_settlement_totals(self.cash_advance_request)

	def on_cancel(self):
		cancel_journal_entry(self.journal_entry)
		frappe.db.set_value(self.doctype, self.name, "journal_entry", None, update_modified=False)
		sync_cash_advance_request_settlement_totals(self.cash_advance_request)

	def _validate_fund_source_company(self):
		if not self.fund_source or not self.company:
			return
		acc_company = frappe.db.get_value("Account", self.fund_source, "company")
		if acc_company and acc_company != self.company:
			frappe.throw(
				_("Fund Source Account does not belong to selected Company. Filter Fund Source by the Company.")
			)

	def _validate_linked_request(self):
		if not self.cash_advance_request:
			return
		if not frappe.db.exists("Cash Advance Request", self.cash_advance_request):
			frappe.throw(_("Cash Advance Request {0} does not exist.").format(self.cash_advance_request))
		req_co = frappe.db.get_value("Cash Advance Request", self.cash_advance_request, "company")
		if req_co and self.company and req_co != self.company:
			frappe.throw(_("Company must match the linked Cash Advance Request."))

	def _validate_settlement_amount(self):
		if not self.cash_advance_request or not self.acknowledgment_type or flt(self.amount, 2) <= 0:
			return
		summary = get_cash_advance_settlement_summary(
			self.cash_advance_request, exclude_acknowledgment=self.name
		)
		amount = flt(self.amount, 2)
		if self.acknowledgment_type == "Receipt" and amount > summary["cash_to_return"] + 0.01:
			frappe.throw(
				_("Receipt amount {0} exceeds unused cash still to return ({1}).").format(
					amount, summary["cash_to_return"]
				)
			)
		if self.acknowledgment_type == "Payment" and amount > summary["cash_to_pay"] + 0.01:
			frappe.throw(
				_("Payment amount {0} exceeds additional cash still to pay ({1}).").format(
					amount, summary["cash_to_pay"]
				)
			)
