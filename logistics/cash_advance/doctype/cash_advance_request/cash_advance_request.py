# -*- coding: utf-8 -*-
# Copyright (c) 2025, AgilaSoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, date_diff, flt, fmt_money, formatdate, get_link_to_form, getdate, nowdate, today

from logistics.cash_advance.accounting import (
	_validate_cash_bank_account,
	cancel_journal_entry,
	create_advance_release_journal_entry,
	ensure_payee_for_party_accounts,
)
from logistics.cash_advance.doctype.cash_advance_settings.cash_advance_settings import (
	get_max_due_date_extension_days,
)
from logistics.cash_advance.job_charge_items import get_item_codes_for_job_number
from logistics.cash_advance.job_number_rules import row_requires_job_number
from logistics.cash_advance.totals_sync import (
	compute_unliquidated,
	get_cash_advance_request_totals,
	get_release_journal_entry,
)


class CashAdvanceRequest(Document):
	@property
	def total_liquidated(self) -> float:
		return flt(self._request_totals().get("total_liquidated"))

	@property
	def returned(self) -> float:
		return flt(self._request_totals().get("returned"))

	@property
	def refunded(self) -> float:
		return flt(self._request_totals().get("refunded"))

	@property
	def unliquidated(self) -> float:
		return flt(self._request_totals().get("unliquidated"))

	@property
	def advance_journal_entry(self):
		if not self.name or self.name.startswith("new-"):
			return None
		return get_release_journal_entry(self.name)

	def _request_totals(self) -> dict:
		cache_key = "_logistics_cash_advance_request_totals"
		if not hasattr(self, cache_key):
			if not self.name or self.name.startswith("new-"):
				totals = {
					"total_requested": flt(self.total_requested, 2),
					"total_liquidated": 0,
					"returned": 0,
					"refunded": 0,
					"unliquidated": flt(self.total_requested, 2),
				}
			else:
				totals = get_cash_advance_request_totals(self.name)
				totals["unliquidated"] = compute_unliquidated(
					flt(self.total_requested if self.total_requested is not None else totals.get("total_requested")),
					totals.get("total_liquidated", 0),
					totals.get("returned", 0),
					totals.get("refunded", 0),
				)
			setattr(self, cache_key, totals)
		return getattr(self, cache_key)

	def validate(self):
		self._validate_no_overdue_advance_for_payee()
		self._validate_accounting_dimensions()
		self._validate_fund_source_company()
		self._validate_fund_source_fund_type()
		self._sync_require_job_number_from_fund_source()
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

	def _sync_require_job_number_from_fund_source(self):
		if not self.fund_source:
			return
		self.require_job_number = cint(
			frappe.db.get_value("Account", self.fund_source, "require_job_number")
		)

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
		unliquidated_expr = (
			"IFNULL(car.total_requested, 0) - IFNULL(liq.total_liquidated, 0) "
			"+ IFNULL(ack.refunded, 0) - IFNULL(ack.returned, 0)"
		)
		overdue = frappe.db.sql(
			f"""
			SELECT
				car.name,
				car.liquidation_due_date,
				({unliquidated_expr}) AS unliquidated,
				DATEDIFF(%(today)s, car.liquidation_due_date) AS days_overdue
			FROM `tabCash Advance Request` car
			LEFT JOIN (
				SELECT cash_advance_request, SUM(total_liquidated) AS total_liquidated
				FROM `tabCash Advance Liquidation`
				WHERE docstatus = 1
				GROUP BY cash_advance_request
			) liq ON liq.cash_advance_request = car.name
			LEFT JOIN (
				SELECT
					cash_advance_request,
					SUM(CASE WHEN acknowledgment_type = 'Receipt' THEN amount ELSE 0 END) AS returned,
					SUM(CASE WHEN acknowledgment_type = 'Payment' THEN amount ELSE 0 END) AS refunded
				FROM `tabCash Acknowledgment`
				WHERE docstatus = 1
				GROUP BY cash_advance_request
			) ack ON ack.cash_advance_request = car.name
			WHERE car.payee = %(payee)s
			  AND car.docstatus = 1
			  AND ({unliquidated_expr}) > 0
			  AND car.liquidation_due_date IS NOT NULL
			  AND car.liquidation_due_date < %(today)s
			  AND car.name != %(self_name)s
			ORDER BY car.liquidation_due_date ASC
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
		if get_release_journal_entry(self.name):
			return
		create_advance_release_journal_entry(self)

	def on_cancel(self):
		cancel_journal_entry(get_release_journal_entry(self.name))

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

	def _validate_items_against_job(self):
		for idx, row in enumerate(self.items or [], start=1):
			if not row.item_code:
				continue
			if not row_requires_job_number(self.require_job_number, row.item_code):
				continue
			if not row.job_number:
				frappe.throw(_("Row {0}: Job Number is required for this charge item.").format(idx))
			self._validate_item_job_number_company(row.job_number)
			allowed = set(get_item_codes_for_job_number(row.job_number))
			if row.item_code not in allowed:
				frappe.throw(
					_("Row {0}: Charge Item {1} is not on the charges for Job Number {2}.").format(
						idx, row.item_code, row.job_number
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
		if hasattr(self, "_logistics_cash_advance_request_totals"):
			delattr(self, "_logistics_cash_advance_request_totals")
		totals = self._request_totals()

		return {
			"total_requested": total_requested,
			"total_liquidated": flt(totals.get("total_liquidated")),
			"unliquidated": flt(totals.get("unliquidated")),
		}


@frappe.whitelist()
def extend_liquidation_due_date(
	cash_advance_request,
	liquidation_due_date,
	reason_code=None,
	reason_description=None,
):
	"""Extend liquidation due date on a submitted cash advance with an outstanding balance."""
	if not cash_advance_request:
		frappe.throw(_("Cash Advance Request is required."))
	frappe.has_permission("Cash Advance Request", "write", doc=cash_advance_request, throw=True)

	if not reason_code:
		frappe.throw(_("Reason Code is required."), title=_("Missing Reason Code"))
	if not reason_description or not str(reason_description).strip():
		frappe.throw(_("Reason Description is required."), title=_("Missing Reason Description"))

	if not frappe.db.exists("Cash Advance Reason Code", reason_code):
		frappe.throw(_("Reason Code {0} does not exist.").format(reason_code))
	if not cint(frappe.db.get_value("Cash Advance Reason Code", reason_code, "is_active")):
		frappe.throw(_("Reason Code {0} is not active.").format(reason_code))

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
		extension_days = date_diff(new_due, old_d)
	else:
		extension_days = date_diff(new_due, today_d)

	max_extension_days = get_max_due_date_extension_days(doc.company)
	if max_extension_days > 0 and extension_days > max_extension_days:
		frappe.throw(
			_(
				"Due date extension of {0} day(s) exceeds the maximum allowed extension of {1} day(s) for company {2}."
			).format(extension_days, max_extension_days, doc.company),
			title=_("Extension Limit Exceeded"),
		)

	reason_label = reason_code
	reason_master_description = frappe.db.get_value(
		"Cash Advance Reason Code", reason_code, "description"
	)
	if reason_master_description:
		reason_label = f"{reason_code} ({reason_master_description})"

	reason_text = str(reason_description).strip()
	prefix = _("Due date extended to {0} [{1}]: ").format(formatdate(new_due), reason_label)
	existing = (doc.status_reason or "").strip()
	status_reason = (existing + "\n" + prefix + reason_text).strip() if existing else prefix + reason_text

	frappe.db.set_value(
		"Cash Advance Request",
		doc.name,
		{
			"liquidation_due_date": new_due,
			"status_reason": status_reason,
		},
		update_modified=True,
	)

	return {
		"success": True,
		"liquidation_due_date": str(new_due),
		"message": _("Liquidation Due Date extended to {0}.").format(formatdate(new_due)),
	}
