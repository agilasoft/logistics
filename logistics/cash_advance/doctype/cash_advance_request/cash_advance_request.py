# -*- coding: utf-8 -*-
# Copyright (c) 2025, AgilaSoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, fmt_money, formatdate, get_link_to_form, nowdate

from logistics.cash_advance.accounting import (
	_validate_cash_bank_account,
	cancel_journal_entry,
	create_advance_release_journal_entry,
	ensure_payee_for_party_accounts,
)
from logistics.cash_advance.job_charge_items import get_item_codes_for_job_number


class CashAdvanceRequest(Document):
	def validate(self):
		self._validate_no_overdue_advance_for_payee()
		self._validate_job_number_company_alignment()
		self._validate_items_against_job()

		if self.total_requested and self.total_requested < 0:
			frappe.throw(_("Total Requested cannot be negative"))

		self.calculate_total()

	def _validate_no_overdue_advance_for_payee(self):
		"""Block draft Cash Advance Requests when the payee has any submitted
		advance whose liquidation due date has already passed and that is not
		fully liquidated. Amendments are allowed so an overdue request can
		still be corrected."""
		if cint(self.docstatus) != 0:
			return
		if self.amended_from:
			return
		if not self.payee:
			return

		today = nowdate()
		overdue = frappe.db.sql(
			"""
			SELECT
				name,
				liquidation_due_date,
				unliquidated,
				DATEDIFF(%(today)s, liquidation_due_date) AS days_overdue
			FROM `tabCash Advance Request`
			WHERE payee = %(payee)s
			  AND docstatus = 1
			  AND IFNULL(unliquidated, 0) > 0
			  AND liquidation_due_date IS NOT NULL
			  AND liquidation_due_date < %(today)s
			  AND name != %(self_name)s
			ORDER BY liquidation_due_date ASC
			LIMIT 5
			""",
			{
				"today": today,
				"payee": self.payee,
				"self_name": self.name or "",
			},
			as_dict=True,
		)

		if not overdue:
			return

		lines = "<br>".join(
			_("{0} — due {1} ({2} day(s) overdue, unliquidated {3})").format(
				get_link_to_form("Cash Advance Request", row.name),
				formatdate(row.liquidation_due_date),
				cint(row.days_overdue),
				fmt_money(flt(row.unliquidated), currency=frappe.defaults.get_global_default("currency")),
			)
			for row in overdue
		)

		frappe.throw(
			_(
				"Payee {0} has overdue unliquidated Cash Advance Request(s)."
				" Liquidate the following before creating a new request:<br>{1}"
			).format(frappe.bold(self.payee_name or self.payee), lines),
			title=_("Overdue Cash Advance"),
		)

	def before_submit(self):
		self.calculate_total()
		if not self.fund_source:
			frappe.throw(_("Fund Source (Bank or Cash account) is required to submit."))
		if not self.payee:
			frappe.throw(_("Payee (Supplier) is required to submit (used as the party on the advance entry)."))
		_validate_cash_bank_account(self.fund_source, self.company)
		ensure_payee_for_party_accounts(self)
		if flt(self.total_requested, 2) <= 0:
			frappe.throw(_("Total Requested must be greater than zero to submit."))

	def on_submit(self):
		if frappe.db.get_value(self.doctype, self.name, "advance_journal_entry"):
			return
		je_name = create_advance_release_journal_entry(self)
		frappe.db.set_value(self.doctype, self.name, "advance_journal_entry", je_name, update_modified=False)

	def on_cancel(self):
		cancel_journal_entry(self.advance_journal_entry)
		frappe.db.set_value(self.doctype, self.name, "advance_journal_entry", None, update_modified=False)

	def _validate_job_number_company_alignment(self):
		if not self.job_number:
			return
		jn = frappe.get_doc("Job Number", self.job_number)
		if jn.company and self.company and jn.company != self.company:
			frappe.throw(
				_("Company {0} does not match Job Number {1} ({2}).").format(
					self.company, self.job_number, jn.company
				)
			)

	def _validate_items_against_job(self):
		if not self.job_number:
			if any(getattr(r, "item_code", None) for r in self.items or []):
				frappe.throw(_("Set Job Number before adding charge items."))
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
