# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors

"""Journal entries for cash advance release and liquidation."""

from __future__ import unicode_literals

from typing import Any, Dict, Optional

import frappe
from frappe import _
from frappe.utils import cint, flt

from logistics.cash_advance.totals_sync import _sum_submitted_acknowledgments, get_release_journal_entry
from logistics.job_management.recognition_engine import apply_journal_entry_posting_header_from_job
from logistics.utils.item_accounts import get_expense_account_for_item  # re-export


def get_ar_employee_account(company: Optional[str] = None) -> str:
	"""A/R employee (advance) control account from per-company Cash Advance Settings."""
	from logistics.cash_advance.doctype.cash_advance_settings.cash_advance_settings import CashAdvanceSettings

	if not company:
		company = frappe.defaults.get_user_default("Company")
	if not company:
		frappe.throw(_("Company is required to resolve Cash Advance Settings."))
	if not frappe.db.exists("DocType", "Cash Advance Settings"):
		frappe.throw(_("Install Cash Advance Settings DocType first."))
	settings = CashAdvanceSettings.get_settings(company)
	if not settings:
		frappe.throw(
			_("Create Cash Advance Settings for company {0} (run migrate or open the form once).").format(
				company
			)
		)
	if not settings.ar_employee_account:
		frappe.throw(
			_("Set A/R Employee (Employee Advance) in Cash Advance Settings for company {0}.").format(
				company
			)
		)
	return settings.ar_employee_account


def _validate_cash_bank_account(account: str, company: str) -> None:
	if not account or not frappe.db.exists("Account", account):
		frappe.throw(_("Invalid account {0}.").format(account))
	acc_company, acc_type, disabled, is_group, fund_type = frappe.db.get_value(
		"Account", account, ["company", "account_type", "disabled", "is_group", "fund_type"]
	)
	if acc_company != company:
		frappe.throw(
			_("Fund Source Account does not belong to selected Company. Filter Fund Source by the Company.")
		)
	if cint(disabled) or cint(is_group):
		frappe.throw(_("Fund source must be a leaf Bank or Cash account."))
	if acc_type not in ("Bank", "Cash"):
		frappe.throw(_("Fund source must be a Bank or Cash account."))
	if not fund_type:
		frappe.throw(_("Fund Source {0} must have Fund Type set on the GL Account.").format(account))


def _employee_advance_doctype_installed() -> bool:
	return bool(frappe.db.get_value("DocType", "Employee Advance", "name"))


def _resolve_employee_advance_name(source_doc) -> Optional[str]:
	if not source_doc:
		return None
	ea = getattr(source_doc, "employee_advance", None)
	if not ea and getattr(source_doc, "doctype", None) in ("Cash Advance Liquidation", "Cash Acknowledgment"):
		req = getattr(source_doc, "cash_advance_request", None)
		if req:
			ea = frappe.db.get_value("Cash Advance Request", req, "employee_advance")
	return ea


def _je_account_reference(source_doc) -> Dict[str, str]:
	"""Optional Employee Advance reference for liquidation lines. Returns {} when not configured."""
	if not source_doc or not getattr(source_doc, "name", None):
		return {}
	if not _employee_advance_doctype_installed():
		return {}
	ea = _resolve_employee_advance_name(source_doc)
	if not ea:
		return {}
	if not frappe.db.exists("Employee Advance", ea):
		frappe.throw(_("Employee Advance {0} does not exist.").format(ea))
	ea_company = frappe.db.get_value("Employee Advance", ea, "company")
	src_company = getattr(source_doc, "company", None)
	if ea_company and src_company and ea_company != src_company:
		frappe.throw(_("Employee Advance {0} belongs to a different company.").format(ea))
	return {"reference_type": "Employee Advance", "reference_name": ea}


def _je_dimension_fields(source_doc) -> Dict[str, Any]:
	out = {}
	if not source_doc:
		return out
	for fn in ("branch", "cost_center", "profit_center", "project"):
		val = getattr(source_doc, fn, None)
		if val:
			out[fn] = val
	jn = getattr(source_doc, "job_number", None)
	if jn:
		out["job_number"] = jn
	return out


def _resolve_payee_supplier(source_doc) -> Optional[str]:
	"""Supplier payee on the document, or from linked Cash Advance Request (liquidation)."""
	if not source_doc:
		return None
	payee = getattr(source_doc, "payee", None)
	if payee:
		return payee
	req = getattr(source_doc, "cash_advance_request", None)
	if req:
		return frappe.db.get_value("Cash Advance Request", req, "payee")
	return None


def _account_requires_party(account: str) -> bool:
	acc_type = frappe.get_cached_value("Account", account, "account_type")
	return acc_type in ("Receivable", "Payable")


def _party_fields_for_account(account: str, source_doc) -> Dict[str, str]:
	"""ERPNext requires party on Receivable / Payable accounts (e.g. Creditors)."""
	if not account or not _account_requires_party(account):
		return {}
	payee = _resolve_payee_supplier(source_doc)
	if not payee:
		frappe.throw(
			_("Payee (Supplier) is required when posting to receivable/payable account {0}.").format(account)
		)
	return {"party_type": "Supplier", "party": payee}


def ensure_payee_for_party_accounts(source_doc) -> None:
	"""Supplier payee required when any posted account is Receivable/Payable (e.g. Creditors)."""
	payee = _resolve_payee_supplier(source_doc)
	accounts = [get_ar_employee_account(getattr(source_doc, "company", None))]
	if getattr(source_doc, "doctype", None) == "Cash Advance Liquidation":
		co = getattr(source_doc, "company", None)
		for row in source_doc.get("items") or []:
			ic = getattr(row, "item_code", None)
			if not ic or not co:
				continue
			ea = get_expense_account_for_item(ic, co)
			if ea:
				accounts.append(ea)
	if any(_account_requires_party(a) for a in accounts if a) and not payee:
		frappe.throw(
			_("Payee (Supplier) is required for receivable/payable accounts used on this entry (set Payee or load from Cash Advance Request).")
		)


def _backfill_party_on_receivable_payable_rows(je, source_doc) -> None:
	"""Safety net: ERPNext validate_party requires party on Receivable/Payable lines."""
	payee = _resolve_payee_supplier(source_doc)
	if not payee:
		return
	for d in je.get("accounts") or []:
		acc = getattr(d, "account", None)
		if not acc:
			continue
		at = frappe.get_cached_value("Account", acc, "account_type")
		if at not in ("Receivable", "Payable"):
			continue
		if getattr(d, "party_type", None) and getattr(d, "party", None):
			continue
		d.party_type = "Supplier"
		d.party = payee


def _first_line_job_number(source_doc) -> Optional[str]:
	for row in source_doc.get("items") or []:
		jn = getattr(row, "job_number", None)
		if jn:
			return jn
	return None


def _posting_header_context(source_doc):
	"""Resolve company/branch/job_number for mandatory Journal Entry posting header fields."""
	if getattr(source_doc, "branch", None) or getattr(source_doc, "job_number", None):
		return source_doc
	jn = _first_line_job_number(source_doc)
	if not jn:
		return source_doc
	ctx = frappe._dict(source_doc.as_dict())
	ctx.job_number = jn
	return ctx


def _apply_je_posting_header(je, source_doc) -> None:
	"""Populate site-specific mandatory Journal Entry header fields (e.g. Posting Company/Branch)."""
	apply_journal_entry_posting_header_from_job(je, _posting_header_context(source_doc))


def _append_je_line(je, account: str, debit: float, credit: float, source_doc, is_advance: bool = False):
	if not account:
		return
	debit = flt(debit, 2)
	credit = flt(credit, 2)
	if debit <= 0 and credit <= 0:
		return
	row: Dict[str, Any] = {
		"account": account,
		"debit_in_account_currency": debit,
		"credit_in_account_currency": credit,
	}
	# Advance entries are anchored by party + is_advance; ERPNext rejects a reference_type alongside that.
	if not is_advance:
		row.update(_je_account_reference(source_doc))
	child_meta = frappe.get_meta("Journal Entry Account")
	for fieldname, value in _je_dimension_fields(source_doc).items():
		if value and child_meta.has_field(fieldname):
			row[fieldname] = value
	# Do not gate party on child_meta.has_field — some customizations omit Link fields from meta
	# while ERPNext still validates party on submit.
	row.update(_party_fields_for_account(account, source_doc))
	if is_advance:
		row["is_advance"] = "Yes"
	je.append("accounts", row)


def create_advance_release_journal_entry(doc) -> str:
	"""Post a Supplier Advance Entry: Dr Advance account (party = Payee, is_advance=Yes), Cr Cash/Bank."""
	if doc.name and frappe.db.exists(doc.doctype, doc.name):
		existing = get_release_journal_entry(doc.name)
		if existing:
			return existing

	_validate_cash_bank_account(doc.fund_source, doc.company)
	ar = get_ar_employee_account(doc.company)

	payee = _resolve_payee_supplier(doc)
	if not payee:
		frappe.throw(_("Payee (Supplier) is required to release a cash advance under a Payee."))

	ar_type = frappe.get_cached_value("Account", ar, "account_type")
	if ar_type not in ("Receivable", "Payable"):
		frappe.throw(
			_("Advance account {0} must be of type Receivable or Payable to post an Advance Entry under the Payee.").format(ar)
		)

	amount = flt(doc.total_requested, 2)
	if amount <= 0:
		frappe.throw(_("Total Requested must be greater than zero to release cash."))

	fund_acc_type = frappe.get_cached_value("Account", doc.fund_source, "account_type")
	voucher_type = "Bank Entry" if fund_acc_type == "Bank" else "Cash Entry"

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = voucher_type
	je.company = doc.company
	je.posting_date = doc.release_date or doc.date
	je.bill_no = doc.name
	je.user_remark = _("Cash advance released {0} to {1}").format(doc.name, payee)

	_append_je_line(je, ar, amount, 0, doc, is_advance=True)
	_append_je_line(je, doc.fund_source, 0, amount, doc)
	_backfill_party_on_receivable_payable_rows(je, doc)
	_apply_je_posting_header(je, doc)

	je.flags.ignore_permissions = True
	je.insert()
	je.submit()

	return je.name


def cancel_journal_entry(je_name: Optional[str]) -> None:
	if not je_name or not frappe.db.exists("Journal Entry", je_name):
		return
	je = frappe.get_doc("Journal Entry", je_name)
	if je.docstatus == 1:
		je.flags.ignore_permissions = True
		je.cancel()



def create_liquidation_journal_entry(doc) -> str:
	"""Post expense lines only (Dr cost, Cr A/R). Cash settlement is via Cash Acknowledgment."""
	if doc.name and frappe.db.exists(doc.doctype, doc.name):
		existing = frappe.db.get_value(doc.doctype, doc.name, "liquidation_journal_entry")
		if existing:
			return existing

	if not doc.cash_advance_request:
		frappe.throw(_("Cash Advance Request is required to post liquidation."))
	if frappe.db.get_value("Cash Advance Request", doc.cash_advance_request, "docstatus") != 1:
		frappe.throw(_("Cash Advance Request must be submitted before liquidation."))

	ar = get_ar_employee_account(doc.company)

	posting_date = getattr(doc, "posting_date", None) or doc.liquidation_date or doc.request_date
	if not posting_date:
		posting_date = frappe.utils.today()

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Journal Entry"
	je.company = doc.company
	je.posting_date = posting_date
	je.user_remark = _("Cash advance liquidation {0}").format(doc.name)

	expense_total = 0.0
	for row in doc.get("items") or []:
		amt = flt(row.amount_liquidated, 2)
		if amt <= 0:
			continue
		exp_acc = get_expense_account_for_item(row.item_code, doc.company)
		if not exp_acc:
			frappe.throw(
				_("No expense / purchase account for item {0} in company {1}.").format(
					row.item_code, doc.company
				)
			)
		_append_je_line(je, exp_acc, amt, 0, doc)
		_append_je_line(je, ar, 0, amt, doc)
		expense_total += amt

	expense_total = flt(expense_total, 2)
	if expense_total <= 0:
		frappe.throw(_("Total liquidated amount must be greater than zero."))

	_backfill_party_on_receivable_payable_rows(je, doc)
	_apply_je_posting_header(je, doc)

	je.flags.ignore_permissions = True
	je.insert()
	je.submit()

	return je.name


@frappe.whitelist()
def get_cash_advance_settlement_summary(cash_advance_request: str, exclude_acknowledgment: Optional[str] = None) -> Dict[str, float]:
	"""Outstanding cash to return (Receipt) or pay (Payment) after liquidations and prior acknowledgments."""
	advance = flt(
		frappe.db.get_value("Cash Advance Request", cash_advance_request, "total_requested"), 2
	)
	liquidated = flt(
		frappe.db.sql(
			"""
			SELECT COALESCE(SUM(total_liquidated), 0)
			FROM `tabCash Advance Liquidation`
			WHERE cash_advance_request = %s AND docstatus = 1
			""",
			cash_advance_request,
		)[0][0],
		2,
	)
	receipts = _sum_submitted_acknowledgments(cash_advance_request, "Receipt", exclude_acknowledgment)
	payments = _sum_submitted_acknowledgments(cash_advance_request, "Payment", exclude_acknowledgment)
	cash_to_return = flt(max(advance - liquidated - receipts, 0), 2)
	cash_to_pay = flt(max(liquidated - advance - payments, 0), 2)
	return {
		"advance": advance,
		"liquidated": liquidated,
		"receipts": receipts,
		"payments": payments,
		"cash_to_return": cash_to_return,
		"cash_to_pay": cash_to_pay,
	}


def create_cash_acknowledgment_journal_entry(doc) -> str:
	"""Receipt: Dr Cash/Bank, Cr A/R (unused cash returned). Payment: Dr A/R, Cr Cash/Bank (additional payout)."""
	if doc.name and frappe.db.exists(doc.doctype, doc.name):
		existing = frappe.db.get_value(doc.doctype, doc.name, "journal_entry")
		if existing:
			return existing

	if not doc.cash_advance_request:
		frappe.throw(_("Cash Advance Request is required."))
	if frappe.db.get_value("Cash Advance Request", doc.cash_advance_request, "docstatus") != 1:
		frappe.throw(_("Cash Advance Request must be submitted before cash acknowledgment."))

	_validate_cash_bank_account(doc.fund_source, doc.company)
	ar = get_ar_employee_account(doc.company)
	amount = flt(doc.amount, 2)
	if amount <= 0:
		frappe.throw(_("Amount must be greater than zero."))

	ack_type = doc.acknowledgment_type
	if ack_type not in ("Receipt", "Payment"):
		frappe.throw(_("Acknowledgment Type must be Receipt or Payment."))

	summary = get_cash_advance_settlement_summary(doc.cash_advance_request, exclude_acknowledgment=doc.name)
	if ack_type == "Receipt" and amount > summary["cash_to_return"] + 0.01:
		frappe.throw(
			_("Receipt amount {0} exceeds unused cash still to return ({1}).").format(
				amount, summary["cash_to_return"]
			)
		)
	if ack_type == "Payment" and amount > summary["cash_to_pay"] + 0.01:
		frappe.throw(
			_("Payment amount {0} exceeds additional cash still to pay ({1}).").format(
				amount, summary["cash_to_pay"]
			)
		)

	posting_date = getattr(doc, "posting_date", None) or frappe.utils.today()
	fund_acc_type = frappe.get_cached_value("Account", doc.fund_source, "account_type")
	voucher_type = "Bank Entry" if fund_acc_type == "Bank" else "Cash Entry"

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = voucher_type
	je.company = doc.company
	je.posting_date = posting_date
	je.user_remark = _("Cash acknowledgment {0} ({1})").format(doc.name, ack_type)

	if ack_type == "Receipt":
		_append_je_line(je, doc.fund_source, amount, 0, doc)
		_append_je_line(je, ar, 0, amount, doc)
	else:
		_append_je_line(je, ar, amount, 0, doc)
		_append_je_line(je, doc.fund_source, 0, amount, doc)

	_backfill_party_on_receivable_payable_rows(je, doc)
	_apply_je_posting_header(je, doc)

	je.flags.ignore_permissions = True
	je.insert()
	je.submit()

	return je.name
