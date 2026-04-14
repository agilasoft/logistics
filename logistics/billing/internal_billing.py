# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, see license.txt

"""
Internal billing: Journal Entry for Internal Jobs where the operating company matches
the Main Job company. Internal Job is identified by is_internal_job + Main Job link
(on the job or parent booking/order). Intercompany SI/PI is handled separately when
companies differ (see intercompany_invoice).

Revenue (Internal Job) = cost allocated from Main Job; cost = tariff/actual per charge.
JE rows carry Job Number and Item accounting dimensions when configured.
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt, today
from typing import Dict, Any, Optional, List, Tuple

from logistics.job_management.gl_item_dimension import item_row_dict

# Job types that can be internal jobs (same as intercompany for consistency)
INTERNAL_BILLING_JOB_TYPES = (
    "Transport Job",
    "Transport Order",
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


def _internal_billing_jv_user_remark(sales_quote_name: str, trigger_si: Optional[str], company: str) -> str:
    remark = _("Internal Billing - Sales Quote {0} - Company {1}").format(sales_quote_name, company)
    if trigger_si:
        remark += _(" - Trigger SI: {0}").format(trigger_si)
    return remark


def _internal_billing_jv_already_created(sales_quote_name: str, trigger_si: Optional[str], company: str) -> bool:
    """Return True if we already created an internal billing JV for this quote, trigger SI, and company."""
    remark = _internal_billing_jv_user_remark(sales_quote_name, trigger_si, company)
    return bool(
        frappe.db.exists(
            "Journal Entry",
            {"user_remark": remark, "docstatus": 1},
        )
    )


def _append_je_split_rows(
    entries: List[Dict[str, Any]],
    expense_account: str,
    income_account: str,
    payable_account: Optional[str],
    job_doc,
    revenue: float,
    cost: float,
    item_code: Optional[str],
    je_row_has_jcn: bool,
) -> None:
    """Append balanced Dr/Cr rows for one charge split; uses internal job cost_center / JCN / item dimension."""
    cost_center = getattr(job_doc, "cost_center", None)
    profit_center = getattr(job_doc, "profit_center", None)
    ref_type = getattr(job_doc, "doctype", None)
    ref_name = getattr(job_doc, "name", None)
    jcn = getattr(job_doc, "job_number", None)
    job_type = ref_type
    job_no = ref_name

    item_dim = item_row_dict("Journal Entry Account", item_code) if item_code else {}

    def base_row(user_remark: str) -> Dict[str, Any]:
        row = {
            "cost_center": cost_center,
            "profit_center": profit_center,
            "reference_type": ref_type,
            "reference_name": ref_name,
            "user_remark": user_remark,
        }
        row.update(item_dim)
        if je_row_has_jcn and jcn:
            row["job_number"] = jcn
        return row

    if flt(revenue) > 0:
        entries.append(
            {
                **base_row(_("{0} {1} - Internal cost allocation").format(job_type, job_no)),
                "account": expense_account,
                "debit_in_account_currency": flt(revenue, 2),
                "credit_in_account_currency": 0,
            }
        )
        entries.append(
            {
                **base_row(_("{0} {1} - Internal revenue").format(job_type, job_no)),
                "account": income_account,
                "debit_in_account_currency": 0,
                "credit_in_account_currency": flt(revenue, 2),
            }
        )
    if flt(cost) > 0 and payable_account and payable_account != expense_account:
        entries.append(
            {
                **base_row(_("{0} {1} - Internal cost (tariff/actual)").format(job_type, job_no)),
                "account": expense_account,
                "debit_in_account_currency": flt(cost, 2),
                "credit_in_account_currency": 0,
            }
        )
        entries.append(
            {
                **base_row(_("{0} {1} - Internal cost accrual").format(job_type, job_no)),
                "account": payable_account,
                "debit_in_account_currency": 0,
                "credit_in_account_currency": flt(cost, 2),
            }
        )


def create_internal_billing_journal_entries_for_quote(
    sales_quote_name: str,
    trigger_si: Optional[str] = None,
    posting_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    For each Internal Job on the quote where job.company == Main Job company, build Journal Entry
    lines (per charge) with Job Number and Item dimensions. One JE per company.
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

    from logistics.billing.cross_module_billing import (
        get_all_billing_jobs_from_sales_quote,
        resolve_internal_job_main_job,
        get_main_job_company,
        iter_internal_job_charge_splits,
    )

    all_jobs = get_all_billing_jobs_from_sales_quote(sales_quote)
    je_row_has_jcn = bool(frappe.get_meta("Journal Entry Account").get_field("job_number"))

    # company -> list of entry dicts
    by_company: Dict[str, List[Dict[str, Any]]] = {}

    for job_type, job_no in all_jobs:
        if job_type not in INTERNAL_BILLING_JOB_TYPES:
            continue
        if (job_type, job_no) == (main_job_type, main_job_no):
            continue
        mt, mn = resolve_internal_job_main_job(job_type, job_no)
        if not mt or not mn:
            continue
        main_co = get_main_job_company(mt, mn)
        if not main_co:
            continue
        try:
            job_doc = frappe.get_doc(job_type, job_no)
        except Exception:
            continue
        op_co = getattr(job_doc, "company", None)
        if not op_co or op_co != main_co:
            continue

        splits = list(iter_internal_job_charge_splits(job_type, job_no, customer=end_customer))
        if not splits:
            continue
        if op_co not in by_company:
            by_company[op_co] = []
        expense_account, income_account = _get_company_internal_transfer_accounts(op_co)
        if not expense_account or not income_account:
            return {
                "success": False,
                "created": 0,
                "message": _(
                    "Company {0}: set default Expense and Income accounts (or at least one leaf account of each root type) for internal billing."
                ).format(op_co),
            }
        payable_account = frappe.db.get_value("Company", op_co, "default_payable_account")
        for split in splits:
            rev = flt(split.get("revenue"))
            cst = flt(split.get("cost"))
            if rev <= 0 and cst <= 0:
                continue
            _append_je_split_rows(
                by_company[op_co],
                expense_account,
                income_account,
                payable_account,
                job_doc,
                rev,
                cst,
                split.get("item_code"),
                je_row_has_jcn,
            )

    journal_entries: List[str] = []

    for company, entries in by_company.items():
        if not entries:
            continue
        if _internal_billing_jv_already_created(sales_quote_name, trigger_si, company):
            continue

        total_debit = sum(flt(e.get("debit_in_account_currency"), 2) for e in entries)
        total_credit = sum(flt(e.get("credit_in_account_currency"), 2) for e in entries)
        if abs(total_debit - total_credit) > 0.01:
            return {
                "success": False,
                "created": 0,
                "message": _("Internal billing entries do not balance for company {0} (Debit {1} vs Credit {2}).").format(
                    company, total_debit, total_credit
                ),
            }

        user_remark = _internal_billing_jv_user_remark(sales_quote_name, trigger_si, company)

        je = frappe.new_doc("Journal Entry")
        je.posting_date = posting_date
        je.company = company
        je.voucher_type = "Journal Entry"
        je.user_remark = user_remark
        if getattr(sales_quote, "branch", None):
            je.branch = sales_quote.branch
        if getattr(sales_quote, "cost_center", None):
            je.cost_center = sales_quote.cost_center

        je_acc_meta = frappe.get_meta("Journal Entry Account")
        fixed_keys = frozenset(
            {
                "account",
                "debit_in_account_currency",
                "credit_in_account_currency",
                "cost_center",
                "profit_center",
                "reference_type",
                "reference_name",
                "user_remark",
                "job_number",
            }
        )
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
            if je_row_has_jcn and e.get("job_number"):
                row.job_number = e["job_number"]
            for k, v in e.items():
                if k in fixed_keys or not v:
                    continue
                if je_acc_meta.get_field(k):
                    setattr(row, k, v)

        je.flags.ignore_permissions = True
        je.insert()
        je.submit()
        journal_entries.append(je.name)

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

    if not journal_entries:
        return {
            "success": True,
            "created": 0,
            "message": _("No same-company internal jobs with revenue/cost to bill."),
        }

    return {
        "success": True,
        "created": len(journal_entries),
        "journal_entry": journal_entries[-1],
        "journal_entries": journal_entries,
        "message": _("Created {0} Internal Billing Journal Entr(y/ies): {1}.").format(
            len(journal_entries), ", ".join(journal_entries)
        ),
    }


@frappe.whitelist()
def create_internal_billing_for_quote(
    sales_quote_name: str,
    posting_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Manually create internal billing Journal Entry(ies) for same-company Internal Jobs linked to this Sales Quote.
    """
    if not frappe.db.exists("Sales Quote", sales_quote_name):
        frappe.throw(_("Sales Quote {0} not found.").format(sales_quote_name))
    return create_internal_billing_journal_entries_for_quote(
        sales_quote_name=sales_quote_name,
        trigger_si=None,
        posting_date=posting_date or today(),
    )
