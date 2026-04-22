# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors

"""Journal entries for cash advance release and liquidation."""

from __future__ import unicode_literals

from typing import Any, Dict, Optional

import frappe
from frappe import _
from frappe.utils import cint, flt


def get_ar_employee_account() -> str:
	"""A/R employee (advance) control account from Cash Advance Settings."""
	if not frappe.db.exists("DocType", "Cash Advance Settings"):
		frappe.throw(_("Install Cash Advance Settings DocType first."))
	if not frappe.db.exists("Cash Advance Settings", "Cash Advance Settings"):
		frappe.throw(_("Create Cash Advance Settings (run migrate or open the form once)."))
	settings = frappe.get_doc("Cash Advance Settings", "Cash Advance Settings")
	if not settings.ar_employee_account:
		frappe.throw(_("Set A/R Employee (Employee Advance) in Cash Advance Settings."))
	return settings.ar_employee_account


def _validate_cash_bank_account(account: str, company: str) -> None:
	if not account or not frappe.db.exists("Account", account):
		frappe.throw(_("Invalid account {0}.").format(account))
	acc_company, acc_type, disabled, is_group = frappe.db.get_value(
		"Account", account, ["company", "account_type", "disabled", "is_group"]
	)
	if acc_company != company:
		frappe.throw(_("Account {0} does not belong to company {1}.").format(account, company))
	if cint(disabled) or cint(is_group):
		frappe.throw(_("Fund source must be a leaf Bank or Cash account."))
	if acc_type not in ("Bank", "Cash"):
		frappe.throw(_("Fund source must be a Bank or Cash account."))


def _employee_advance_doctype_installed() -> bool:
	return bool(frappe.db.get_value("DocType", "Employee Advance", "name"))


def _resolve_employee_advance_name(source_doc) -> Optional[str]:
	if not source_doc:
		return None
	ea = getattr(source_doc, "employee_advance", None)
	if not ea and getattr(source_doc, "doctype", None) == "Cash Advance Liquidation":
		req = getattr(source_doc, "cash_advance_request", None)
		if req:
			ea = frappe.db.get_value("Cash Advance Request", req, "employee_advance")
	return ea


def _je_account_reference(source_doc) -> Dict[str, str]:
	"""Journal Entry Account.reference_type must be an ERPNext option (e.g. Employee Advance)."""
	if not source_doc or not getattr(source_doc, "name", None):
		return {}
	if not _employee_advance_doctype_installed():
		return {}
	ea = _resolve_employee_advance_name(source_doc)
	if not ea:
		frappe.throw(
			_("Set Employee Advance on the Cash Advance Request (required for journal entry reference).")
		)
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
	accounts = [get_ar_employee_account()]
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


def _append_je_line(je, account: str, debit: float, credit: float, source_doc):
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
	row.update(_je_account_reference(source_doc))
	child_meta = frappe.get_meta("Journal Entry Account")
	for fieldname, value in _je_dimension_fields(source_doc).items():
		if value and child_meta.has_field(fieldname):
			row[fieldname] = value
	# Do not gate party on child_meta.has_field — some customizations omit Link fields from meta
	# while ERPNext still validates party on submit.
	row.update(_party_fields_for_account(account, source_doc))
	je.append("accounts", row)


def create_advance_release_journal_entry(doc) -> str:
	"""Dr A/R Employee, Cr Fund Source (cash/bank). Returns JE name."""
	if doc.name and frappe.db.exists(doc.doctype, doc.name):
		existing = frappe.db.get_value(doc.doctype, doc.name, "advance_journal_entry")
		if existing:
			return existing

	_validate_cash_bank_account(doc.fund_source, doc.company)
	ar = get_ar_employee_account()

	amount = flt(doc.total_requested, 2)
	if amount <= 0:
		frappe.throw(_("Total Requested must be greater than zero to release cash."))

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Journal Entry"
	je.company = doc.company
	je.posting_date = doc.release_date or doc.date
	je.user_remark = _("Cash advance released {0}").format(doc.name)

	_append_je_line(je, ar, amount, 0, doc)
	_append_je_line(je, doc.fund_source, 0, amount, doc)
	_backfill_party_on_receivable_payable_rows(je, doc)

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


def get_expense_account_for_item(item_code: str, company: str) -> Optional[str]:
	if not item_code:
		return None
	row = frappe.db.sql(
		"""
		SELECT expense_account FROM `tabItem Default`
		WHERE parent=%(item)s AND company=%(co)s
		LIMIT 1
		""",
		{"item": item_code, "co": company},
		as_dict=True,
	)
	if row and row[0].get("expense_account"):
		return row[0].expense_account
	return frappe.db.get_value("Item", item_code, "purchase_account")


def create_liquidation_journal_entry(doc) -> str:
	"""Expense lines (Dr cost, Cr A/R) plus optional cash top-up or return (Dr/Cr cash, Cr/Dr A/R)."""
	if doc.name and frappe.db.exists(doc.doctype, doc.name):
		existing = frappe.db.get_value(doc.doctype, doc.name, "liquidation_journal_entry")
		if existing:
			return existing

	if not doc.cash_advance_request:
		frappe.throw(_("Cash Advance Request is required to post liquidation."))
	if frappe.db.get_value("Cash Advance Request", doc.cash_advance_request, "docstatus") != 1:
		frappe.throw(_("Cash Advance Request must be submitted before liquidation."))

	_validate_cash_bank_account(doc.fund_source, doc.company)
	ar = get_ar_employee_account()

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

	if cint(getattr(doc, "book_cash_balance", 1)):
		advance_amount = flt(
			frappe.db.get_value("Cash Advance Request", doc.cash_advance_request, "total_requested"), 2
		)
		variance = flt(advance_amount - expense_total, 2)
		if abs(variance) >= 0.01:
			if variance > 0:
				# Unused cash returned: Dr Cash, Cr A/R
				_append_je_line(je, doc.fund_source, variance, 0, doc)
				_append_je_line(je, ar, 0, variance, doc)
			else:
				# Additional cash to employee: Dr A/R, Cr Cash
				v = abs(variance)
				_append_je_line(je, ar, v, 0, doc)
				_append_je_line(je, doc.fund_source, 0, v, doc)

	_backfill_party_on_receivable_payable_rows(je, doc)

	je.flags.ignore_permissions = True
	je.insert()
	je.submit()

	return je.name
