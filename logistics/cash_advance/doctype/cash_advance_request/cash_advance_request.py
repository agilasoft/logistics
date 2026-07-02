# -*- coding: utf-8 -*-
# Copyright (c) 2025, AgilaSoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, fmt_money, formatdate, get_link_to_form, getdate, nowdate, today

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
		self._validate_accounting_dimensions()
		self._validate_fund_source_company()
		self._validate_fund_source_fund_type()
		self._validate_request_limit()
		self._validate_items_against_job()

		if self.total_requested and self.total_requested < 0:
			frappe.throw(_("Total Requested cannot be negative"))

		self.calculate_total()

	def _validate_fund_source_company(self):
		if not self.fund_source or not self.company:
			return
		acc_company = frappe.db.get_value("Account", self.fund_source, "company")
		if acc_company and acc_company != self.company:
			frappe.throw(
				_("Fund Source Account does not belong to selected Company. Filter Fund Source by the Company.")
			)

	def _validate_fund_source_fund_type(self):
		if not self.fund_source:
			return
		fund_type = frappe.db.get_value("Account", self.fund_source, "fund_type")
		if not fund_type:
			frappe.throw(
				_("Fund Source {0} must have Fund Type set on the GL Account.").format(
					frappe.bold(self.fund_source)
				)
			)
		if self.fund_type and self.fund_type != fund_type:
			self.fund_type = fund_type

	def _validate_request_limit(self):
		if not self.fund_source:
			return
		limit = flt(frappe.db.get_value("Account", self.fund_source, "cash_advance_request_limit"))
		if limit <= 0:
			return
		self.calculate_total()
		if flt(self.total_requested, 2) > limit:
			frappe.throw(
				_("Total Requested {0} exceeds the Cash Advance Request Limit {1} for Fund Source {2}.").format(
					fmt_money(flt(self.total_requested), currency=frappe.defaults.get_global_default("currency")),
					fmt_money(limit, currency=frappe.defaults.get_global_default("currency")),
					frappe.bold(self.fund_source),
				)
			)

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

	def _validate_accounting_dimensions(self):
		if not self.company:
			return

		if self.cost_center:
			cost_center_company = frappe.db.get_value("Cost Center", self.cost_center, "company")
			if cost_center_company and cost_center_company != self.company:
				frappe.throw(
					_("Cost Center {0} does not belong to Company {1}").format(
						self.cost_center, self.company
					)
				)

		if self.profit_center:
			profit_center_meta = frappe.get_meta("Profit Center")
			for company_field in ("company", "custom_company"):
				if not profit_center_meta.has_field(company_field):
					continue
				try:
					profit_center_company = frappe.db.get_value(
						"Profit Center", self.profit_center, company_field
					)
				except Exception as exc:
					if "Unknown column" in str(exc) or "1054" in str(exc):
						return
					raise
				if profit_center_company and profit_center_company != self.company:
					frappe.throw(
						_("Profit Center {0} does not belong to Company {1}").format(
							self.profit_center, self.company
						)
					)
				return

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
		if self.fund_type == "Revolving Fund":
			for idx, row in enumerate(self.items or [], start=1):
				if not row.item_code and not row.job_number:
					continue
				if not row.job_number:
					frappe.throw(
						_("Row {0}: Job Number is required for Revolving Fund items.").format(idx)
					)
				self._validate_item_job_number_company(row.job_number)
				allowed = set(get_item_codes_for_job_number(row.job_number))
				if row.item_code and row.item_code not in allowed:
					frappe.throw(
						_("Row {0}: Charge Item {1} is not on the charges for Job Number {2}.").format(
							idx, row.item_code, row.job_number
						)
					)
			return

		if not self.job_number:
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

	def _validate_item_job_number_company(self, job_number):
		if not job_number or not self.company:
			return
		jn_company = frappe.db.get_value("Job Number", job_number, "company")
		if jn_company and jn_company != self.company:
			frappe.throw(
				_("Company {0} does not match Job Number {1} ({2}).").format(
					self.company, job_number, jn_company
				)
			)

	def calculate_total(self):
		total_requested = 0

		if self.items:
			for item in self.items:
				if item.amount_requested:
					total_requested += flt(item.amount_requested)

		self.total_requested = total_requested
		self.unliquidated = flt(
			flt(total_requested) - flt(self.total_liquidated) - flt(self.returned) + flt(self.refunded), 2
		)

		return {
			"total_requested": total_requested,
			"total_liquidated": flt(self.total_liquidated),
			"unliquidated": self.unliquidated,
		}


@frappe.whitelist()
def extend_liquidation_due_date(cash_advance_request, liquidation_due_date, reason=None):
	"""Extend liquidation due date on a submitted cash advance with an outstanding balance."""
	if not cash_advance_request:
		frappe.throw(_("Cash Advance Request is required."))
	frappe.has_permission("Cash Advance Request", "write", doc=cash_advance_request, throw=True)

	doc = frappe.get_doc("Cash Advance Request", cash_advance_request)
	if doc.docstatus != 1:
		frappe.throw(_("Only submitted Cash Advance Requests can have the due date extended."))
	if flt(doc.unliquidated, 2) <= 0:
		frappe.throw(_("Cannot extend due date when the cash advance is fully liquidated."))

	new_due = getdate(liquidation_due_date)
	today_d = getdate(today())
	if new_due < today_d:
		frappe.throw(_("New Liquidation Due Date cannot be before today."), title=_("Invalid Date"))

	old_due = doc.liquidation_due_date
	if old_due:
		old_d = getdate(old_due)
		if new_due <= old_d:
			frappe.throw(
				_("New Liquidation Due Date must be after the current due date ({0}).").format(
					formatdate(old_d)
				),
				title=_("Invalid Extension"),
			)

	updates = {"liquidation_due_date": new_due}
	if reason and str(reason).strip():
		prefix = _("Due date extended to {0}: ").format(formatdate(new_due))
		existing = (doc.status_reason or "").strip()
		updates["status_reason"] = (existing + "\n" + prefix + str(reason).strip()).strip() if existing else prefix + str(reason).strip()

	frappe.db.set_value("Cash Advance Request", doc.name, updates, update_modified=True)

	return {
		"success": True,
		"liquidation_due_date": str(new_due),
		"message": _("Liquidation Due Date extended to {0}.").format(formatdate(new_due)),
	}
