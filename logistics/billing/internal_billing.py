# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, see license.txt

"""
Internal billing: Journal Entry for same-company Internal Jobs (non-main legs).
Main Job holds all customer charges; Internal Jobs hold service-specific charges.
Revenue (Internal Job) = Cost of Main Job allocated; Cost = tariff or actual.
When Main Job and Internal Jobs are in the same company, internal billing is
entered through Journal Entry (no Sales Invoice).
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt, today
from typing import Dict, Any, Optional, List, Tuple

# Job types that can be internal jobs (same as intercompany for consistency)
INTERNAL_BILLING_JOB_TYPES = (
    "Transport Job",
    "Air Shipment",
    "Sea Shipment",
    "Warehouse Job",
    "Declaration",
    "Declaration Order",
)


def _get_company_internal_transfer_accounts(company: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Get expense and income accounts for internal transfer (cost allocation / revenue).
    Tries Company default_expense_account, default_income_account; else first leaf account by root_type.
    """
    expense_account = frappe.db.get_value("Company", company, "default_expense_account")
    income_account = frappe.db.get_value("Company", company, "default_income_account")
    if not expense_account:
        acc = frappe.db.get_value(
            "Account",
            {"company": company, "root_type": "Expense", "is_group": 0},
            "name",
            order_by="name",
        )
        expense_account = acc
    if not income_account:
        acc = frappe.db.get_value(
            "Account",
            {"company": company, "root_type": "Income", "is_group": 0},
            "name",
            order_by="name",
        )
        income_account = acc
    return (expense_account, income_account)


def _internal_billing_jv_already_created(sales_quote_name: str, trigger_si: Optional[str]) -> bool:
    """Return True if we already created an internal billing JV for this quote and trigger SI."""
    remark = _("Internal Billing - Sales Quote {0}").format(sales_quote_name)
    if trigger_si:
        remark += _(" - {0}").format(trigger_si)
    return bool(
        frappe.db.exists(
            "Journal Entry",
            {"user_remark": ["like", remark + "%"], "docstatus": 1},
        )
    )


def create_internal_billing_journal_entries_for_quote(
    sales_quote_name: str,
    billing_company: str,
    trigger_si: Optional[str] = None,
    posting_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    For each routing leg where job.company == billing_company and job is not the Main Job,
    create a Journal Entry to record internal billing (revenue = cost of Main Job allocated,
    cost = tariff/actual). Same company only; no Sales Invoice.
    """
    if not frappe.db.exists("Sales Quote", sales_quote_name):
        return {"success": True, "created": 0, "message": _("Sales Quote not found.")}

    sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
    legs = getattr(sales_quote, "routing_legs", None) or []
    if not legs:
        return {"success": True, "created": 0, "message": _("No routing legs.")}

    main_leg = next((r for r in legs if getattr(r, "is_main_job", 0)), None)
    if not main_leg:
        return {"success": True, "created": 0, "message": _("No Main Job on quote.")}

    main_job_type = getattr(main_leg, "job_type", None)
    main_job_no = getattr(main_leg, "job_no", None)
    if not main_job_type or not main_job_no:
        return {"success": True, "created": 0, "message": _("Main Job has no job linked.")}

    posting_date = posting_date or today()
    end_customer = sales_quote.customer

    if _internal_billing_jv_already_created(sales_quote_name, trigger_si):
        return {"success": True, "created": 0, "message": _("Internal billing JV already created for this quote.")}

    from logistics.billing.cross_module_billing import (
        get_all_billing_jobs_from_sales_quote,
        get_internal_job_revenue_and_cost,
    )

    all_jobs = get_all_billing_jobs_from_sales_quote(sales_quote)
    expense_account, income_account = _get_company_internal_transfer_accounts(billing_company)
    if not expense_account or not income_account:
        return {
            "success": False,
            "created": 0,
            "message": _(
                "Company {0}: set default Expense and Income accounts (or at least one leaf account of each root type) for internal billing."
            ).format(billing_company),
        }

    entries: List[Dict[str, Any]] = []  # list of {"account", "debit", "credit", "cost_center", "profit_center", "reference_type", "reference_name"}

    for job_type, job_no in all_jobs:
        if job_type not in INTERNAL_BILLING_JOB_TYPES:
            continue
        if (job_type, job_no) == (main_job_type, main_job_no):
            continue
        try:
            job_doc = frappe.get_doc(job_type, job_no)
        except Exception:
            continue
        operating_company = getattr(job_doc, "company", None)
        if not operating_company or operating_company != billing_company:
            continue

        revenue_total, cost_total = get_internal_job_revenue_and_cost(
            job_type, job_no, customer=end_customer
        )
        if flt(revenue_total) <= 0 and flt(cost_total) <= 0:
            continue

        cost_center = getattr(job_doc, "cost_center", None)
        profit_center = getattr(job_doc, "profit_center", None)
        ref_type = getattr(job_doc, "doctype", job_type)
        ref_name = getattr(job_doc, "name", job_no)

        # Internal Job revenue (allocated from Main Job): Dr Expense (main/cost allocation), Cr Income (internal job revenue)
        if flt(revenue_total) > 0:
            entries.append({
                "account": expense_account,
                "debit_in_account_currency": flt(revenue_total, 2),
                "credit_in_account_currency": 0,
                "cost_center": cost_center,
                "profit_center": profit_center,
                "reference_type": ref_type,
                "reference_name": ref_name,
                "user_remark": _("{0} {1} - Internal cost allocation").format(job_type, job_no),
            })
            entries.append({
                "account": income_account,
                "debit_in_account_currency": 0,
                "credit_in_account_currency": flt(revenue_total, 2),
                "cost_center": cost_center,
                "profit_center": profit_center,
                "reference_type": ref_type,
                "reference_name": ref_name,
                "user_remark": _("{0} {1} - Internal revenue").format(job_type, job_no),
            })
        # Internal Job cost (tariff/actual): Dr Expense (internal job cost), Cr Payable (accrual).
        # Only add if company has a distinct payable account to avoid Dr/Cr same account.
        if flt(cost_total) > 0:
            payable_account = frappe.db.get_value("Company", billing_company, "default_payable_account")
            if payable_account and payable_account != expense_account:
                entries.append({
                    "account": expense_account,
                    "debit_in_account_currency": flt(cost_total, 2),
                    "credit_in_account_currency": 0,
                    "cost_center": cost_center,
                    "profit_center": profit_center,
                    "reference_type": ref_type,
                    "reference_name": ref_name,
                    "user_remark": _("{0} {1} - Internal cost (tariff/actual)").format(job_type, job_no),
                })
                entries.append({
                    "account": payable_account,
                    "debit_in_account_currency": 0,
                    "credit_in_account_currency": flt(cost_total, 2),
                    "cost_center": cost_center,
                    "profit_center": profit_center,
                    "reference_type": ref_type,
                    "reference_name": ref_name,
                    "user_remark": _("{0} {1} - Internal cost accrual").format(job_type, job_no),
                })

    if not entries:
        return {"success": True, "created": 0, "message": _("No same-company internal jobs with revenue/cost to bill.")}

    # Build one Journal Entry with all entries (must balance)
    total_debit = sum(flt(e.get("debit_in_account_currency"), 2) for e in entries)
    total_credit = sum(flt(e.get("credit_in_account_currency"), 2) for e in entries)
    if abs(total_debit - total_credit) > 0.01:
        return {
            "success": False,
            "created": 0,
            "message": _("Internal billing entries do not balance (Debit {0} vs Credit {1}).").format(total_debit, total_credit),
        }

    user_remark = _("Internal Billing - Sales Quote {0}").format(sales_quote_name)
    if trigger_si:
        user_remark += _(" - Trigger SI: {0}").format(trigger_si)

    je = frappe.new_doc("Journal Entry")
    je.posting_date = posting_date
    je.company = billing_company
    je.voucher_type = "Journal Entry"
    je.user_remark = user_remark
    if getattr(sales_quote, "branch", None):
        je.branch = sales_quote.branch
    if getattr(sales_quote, "cost_center", None):
        je.cost_center = sales_quote.cost_center

    for e in entries:
        row = je.append("accounts", {})
        row.account = e["account"]
        row.debit_in_account_currency = flt(e.get("debit_in_account_currency"), 2)
        row.credit_in_account_currency = flt(e.get("credit_in_account_currency"), 2)
        if e.get("cost_center"):
            row.cost_center = e["cost_center"]
        if e.get("profit_center"):
            row.profit_center = e["profit_center"]
        if e.get("reference_type") and e.get("reference_name"):
            row.reference_type = e["reference_type"]
            row.reference_name = e["reference_name"]
        if e.get("user_remark"):
            row.user_remark = e["user_remark"]

    je.flags.ignore_permissions = True
    je.insert()
    je.submit()

    try:
        from logistics.invoice_integration.internal_billing_recognition_reversal import (
            reverse_recognition_for_internal_billing_je,
        )

        reverse_recognition_for_internal_billing_je(je, end_customer)
    except Exception as e:
        frappe.log_error(
            title="Recognition reversal on Internal Billing JE submit",
            message=frappe.get_traceback(),
        )
        frappe.msgprint(
            _("Recognition reversal after internal billing could not be posted: {0}").format(str(e)),
            indicator="orange",
        )

    return {
        "success": True,
        "created": 1,
        "journal_entry": je.name,
        "message": _("Created Internal Billing Journal Entry {0}.").format(je.name),
    }


@frappe.whitelist()
def create_internal_billing_for_quote(
    sales_quote_name: str,
    billing_company: Optional[str] = None,
    posting_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Manually create internal billing Journal Entry for same-company Internal Jobs linked to this Sales Quote.
    billing_company defaults to the quote's company if not provided.
    """
    if not frappe.db.exists("Sales Quote", sales_quote_name):
        frappe.throw(_("Sales Quote {0} not found.").format(sales_quote_name))
    quote = frappe.get_doc("Sales Quote", sales_quote_name)
    company = billing_company or getattr(quote, "company", None)
    if not company:
        frappe.throw(_("Billing company is required. Set company on the Sales Quote or pass billing_company."))
    return create_internal_billing_journal_entries_for_quote(
        sales_quote_name=sales_quote_name,
        billing_company=company,
        trigger_si=None,
        posting_date=posting_date or today(),
    )
