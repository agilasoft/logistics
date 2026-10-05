# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, see license.txt

"""
Internal billing: Journal Entry for linked jobs where the operating company matches
the Main Job company. Linked job is identified by service_role=Linked + Main Service link
(on the job or parent booking/order). Intercompany SI/PI is handled separately when
companies differ (see intercompany_invoice).

Transfers linked-job charge revenue to main-job cost via Dr expense / Cr income per Item.
Each post creates one Journal Entry for linked jobs that do not already have a
submitted internal billing credit. The Sales Quote is not the uniqueness key.
JE rows carry Job Number and Item accounting dimensions when configured.
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint, flt, today
from typing import Dict, Any, Optional, List

from logistics.job_management.gl_item_dimension import item_row_dict
from logistics.utils.item_accounts import get_item_accounts_for_internal_billing

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


def _internal_billing_jv_user_remark(sales_quote_name: str, trigger_si: Optional[str]) -> str:
    remark = _("Internal Billing - Sales Quote {0}").format(sales_quote_name)
    if trigger_si:
        remark += _(" - Trigger SI: {0}").format(trigger_si)
    return remark


def _internal_billing_remark_prefix() -> str:
    """Start of an internal billing Journal Entry remark, before the Sales Quote name."""
    marker = "\x00"
    rendered = _("Internal Billing - Sales Quote {0}").format(marker)
    return rendered.split(marker, 1)[0]


def _linked_revenue_transfer_remark(linked_job_doc) -> str:
    return _("{0} {1} - Internal revenue transfer").format(
        getattr(linked_job_doc, "doctype", None),
        getattr(linked_job_doc, "name", None),
    )


def _linked_job_label(linked_job_doc) -> str:
    return "{0} {1}".format(
        getattr(linked_job_doc, "doctype", None) or "",
        getattr(linked_job_doc, "name", None) or "",
    ).strip()


def _linked_job_internal_billing_already_posted(linked_job_doc, je_row_has_jcn: bool) -> bool:
    """True when a submitted internal billing JE already credits this linked job.

    Cancelled journals (docstatus 2) do not count. Matching uses the linked job's
    Job Number when that row field is present, otherwise the revenue-transfer row remark.
    """
    prefix = _internal_billing_remark_prefix()
    if not prefix:
        return False

    jcn = getattr(linked_job_doc, "job_number", None)
    params: Dict[str, Any] = {"prefix": prefix}
    if je_row_has_jcn and jcn:
        line_match = "jea.job_number = %(job_number)s"
        params["job_number"] = jcn
    else:
        line_match = "jea.user_remark = %(row_remark)s"
        params["row_remark"] = _linked_revenue_transfer_remark(linked_job_doc)

    found = frappe.db.sql(
        """
        SELECT jea.name
        FROM `tabJournal Entry Account` jea
        INNER JOIN `tabJournal Entry` je ON je.name = jea.parent
        WHERE je.docstatus = 1
          AND LOCATE(%(prefix)s, IFNULL(je.user_remark, '')) = 1
          AND IFNULL(jea.credit_in_account_currency, 0) > 0
          AND {line_match}
        LIMIT 1
        """.format(line_match=line_match),
        params,
    )
    return bool(found)


def _job_row_base(job_doc, item_code: Optional[str], je_row_has_jcn: bool) -> Dict[str, Any]:
    row = {
        "cost_center": getattr(job_doc, "cost_center", None),
        "profit_center": getattr(job_doc, "profit_center", None),
    }
    row.update(item_row_dict("Journal Entry Account", item_code) if item_code else {})
    jcn = getattr(job_doc, "job_number", None)
    if je_row_has_jcn and jcn:
        row["job_number"] = jcn
    return row


def _append_revenue_transfer_rows(
    entries: List[Dict[str, Any]],
    main_job_doc,
    linked_job_doc,
    revenue: float,
    item_code: str,
    company: str,
    je_row_has_jcn: bool,
) -> None:
    """Dr main job expense / Cr linked job income for one charge revenue amount."""
    amount = flt(revenue, 2)
    if amount <= 0:
        return

    expense_account, income_account = get_item_accounts_for_internal_billing(item_code, company)
    main_type = getattr(main_job_doc, "doctype", None)
    main_no = getattr(main_job_doc, "name", None)
    linked_type = getattr(linked_job_doc, "doctype", None)
    linked_no = getattr(linked_job_doc, "name", None)

    entries.append(
        {
            **_job_row_base(main_job_doc, item_code, je_row_has_jcn),
            "user_remark": _("{0} {1} - Internal cost from linked service").format(main_type, main_no),
            "account": expense_account,
            "debit_in_account_currency": amount,
            "credit_in_account_currency": 0,
        }
    )
    entries.append(
        {
            **_job_row_base(linked_job_doc, item_code, je_row_has_jcn),
            "user_remark": _("{0} {1} - Internal revenue transfer").format(linked_type, linked_no),
            "account": income_account,
            "debit_in_account_currency": 0,
            "credit_in_account_currency": amount,
        }
    )


def _apply_internal_billing_posting_header(je, billing_main_job) -> None:
    """Copy Company and Branch onto mandatory Posting Company / Posting Branch fields."""
    from logistics.job_management.recognition_engine import (
        _resolve_posting_company_branch,
        apply_journal_entry_posting_header_from_job,
    )

    if billing_main_job and not je.get("branch"):
        job_branch = getattr(billing_main_job, "branch", None)
        if job_branch:
            je.branch = job_branch

    company, branch = _resolve_posting_company_branch(je, billing_main_job)
    if branch and not je.get("branch"):
        je.branch = branch

    meta = frappe.get_meta("Journal Entry")
    missing = []
    for fieldname, value in (
        ("custom_posting_company", company),
        ("posting_company", company),
        ("custom_posting_branch", branch),
        ("posting_branch", branch),
    ):
        df = meta.get_field(fieldname)
        if not df:
            continue
        if value and not je.get(fieldname):
            je.set(fieldname, value)
        if cint(df.reqd) and not je.get(fieldname):
            missing.append(df.label or fieldname)

    if missing:
        frappe.throw(
            _(
                "Cannot create internal billing Journal Entry. Set {0} on the main job or Sales Quote."
            ).format(", ".join(missing)),
            title=_("Journal Entry"),
        )

    apply_journal_entry_posting_header_from_job(je, billing_main_job)


def _submit_internal_billing_journal_entry(
    entries: List[Dict[str, Any]],
    company: str,
    posting_date: str,
    user_remark: str,
    sales_quote,
    end_customer: str,
    billing_main_job=None,
) -> str:
    """Build, submit one Journal Entry from prepared account rows; run recognition reversal."""
    total_debit = sum(flt(e.get("debit_in_account_currency"), 2) for e in entries)
    total_credit = sum(flt(e.get("credit_in_account_currency"), 2) for e in entries)
    if abs(total_debit - total_credit) > 0.01:
        frappe.throw(
            _("Internal billing entries do not balance (Debit {0} vs Credit {1}).").format(
                total_debit, total_credit
            )
        )

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
    je_row_has_jcn = bool(je_acc_meta.get_field("job_number"))
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

    _apply_internal_billing_posting_header(je, billing_main_job)

    je.flags.ignore_permissions = True
    je.flags.ignore_links = True
    # Internal billing posts its own WIP / accrual reversal after submit.
    je.flags.skip_logistics_recognition_reversal = True
    je.insert()
    je.submit()

    try:
        from logistics.invoice_integration.internal_billing_recognition_reversal import (
            reverse_recognition_for_internal_billing_je,
        )

        recognition = reverse_recognition_for_internal_billing_je(
            je, end_customer, billing_main_job=billing_main_job
        )
        parts = []
        if recognition.get("wip_recognition_journal_entry"):
            parts.append(_("WIP recognition: {0}").format(recognition["wip_recognition_journal_entry"]))
        if recognition.get("accrual_recognition_journal_entry"):
            parts.append(_("Accrual recognition: {0}").format(recognition["accrual_recognition_journal_entry"]))
        if recognition.get("wip_journal_entry"):
            parts.append(_("WIP reversal: {0}").format(recognition["wip_journal_entry"]))
        if recognition.get("accrual_journal_entry"):
            parts.append(_("Accrual reversal: {0}").format(recognition["accrual_journal_entry"]))
        if parts:
            frappe.msgprint(" ".join(parts), indicator="green")
    except Exception as e:
        frappe.log_error(
            title="Recognition reversal on Internal Billing JE submit",
            message=frappe.get_traceback(),
        )
        frappe.msgprint(
            _("Recognition reversal after internal billing could not be posted: {0}").format(str(e)),
            indicator="orange",
        )

    return je.name


def create_internal_billing_journal_entries_for_quote(
    sales_quote_name: str,
    trigger_si: Optional[str] = None,
    posting_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    For each linked job on the quote where job.company == Main Job company, build one Journal Entry
    transferring charge revenue to main job cost (per item accounts).

    Linked jobs that already have a submitted internal billing credit are skipped.
    A later post still creates a Journal Entry for linked jobs that have not been billed.
    """
    if not frappe.db.exists("Sales Quote", sales_quote_name):
        return {"success": True, "created": 0, "message": _("Sales Quote not found.")}

    sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
    legs = getattr(sales_quote, "routing_legs", None) or []
    if not legs:
        return {"success": True, "created": 0, "message": _("No routing legs.")}

    from logistics.billing.cross_module_billing import (
        get_all_billing_jobs_from_sales_quote,
        resolve_internal_job_main_job,
        get_main_job_company,
        iter_internal_job_charge_splits,
        iter_main_job_linked_scope_charge_splits,
        resolve_operational_job_for_linked_service,
        linked_job_matches_billing_main,
        resolve_billing_main_job_for_quote,
        is_booking_superseded_by_operational_job,
    )

    quote_main_type, quote_main_no, billing_main_type, billing_main_no = (
        resolve_billing_main_job_for_quote(sales_quote)
    )
    if not quote_main_type or not quote_main_no:
        return {"success": True, "created": 0, "message": _("Main Job has no job linked.")}

    try:
        main_job_doc = frappe.get_doc(billing_main_type, billing_main_no)
    except Exception:
        return {"success": True, "created": 0, "message": _("Main Job document not found.")}

    main_co = getattr(main_job_doc, "company", None)
    if not main_co:
        return {"success": True, "created": 0, "message": _("Main Job has no company.")}

    posting_date = posting_date or today()
    end_customer = sales_quote.customer
    from logistics.utils.internal_job_persistence import resolve_internal_job_for_internal_job_booking

    all_jobs = get_all_billing_jobs_from_sales_quote(sales_quote)
    quote_job_keys = set(all_jobs)
    je_row_has_jcn = bool(frappe.get_meta("Journal Entry Account").get_field("job_number"))

    entries: List[Dict[str, Any]] = []
    missing_item_codes: List[str] = []
    already_billed: List[str] = []
    already_billed_keys = set()
    linked_services_billed_via_operational_job: set = set()
    linked_job_doc_cache: Dict[str, Any] = {}

    def _note_already_billed(linked_job_doc) -> None:
        key = (getattr(linked_job_doc, "doctype", None), getattr(linked_job_doc, "name", None))
        if key in already_billed_keys:
            return
        already_billed_keys.add(key)
        already_billed.append(_linked_job_label(linked_job_doc))

    for job_type, job_no in all_jobs:
        if job_type not in INTERNAL_BILLING_JOB_TYPES:
            continue
        if (job_type, job_no) in (
            (billing_main_type, billing_main_no),
            (quote_main_type, quote_main_no),
        ):
            continue
        if is_booking_superseded_by_operational_job(
            job_type, job_no, quote_job_keys, sales_quote_name=sales_quote_name
        ):
            continue
        mt, mn = resolve_internal_job_main_job(job_type, job_no)
        if not linked_job_matches_billing_main(
            mt, mn, quote_main_type, quote_main_no, billing_main_type, billing_main_no
        ):
            continue
        main_co_check = get_main_job_company(mt, mn) or get_main_job_company(
            billing_main_type, billing_main_no
        )
        if not main_co_check:
            continue
        try:
            linked_job_doc = frappe.get_doc(job_type, job_no)
        except Exception:
            continue
        op_co = getattr(linked_job_doc, "company", None)
        if not op_co or op_co != main_co_check:
            continue
        if _linked_job_internal_billing_already_posted(linked_job_doc, je_row_has_jcn):
            _note_already_billed(linked_job_doc)
            ls_name = resolve_internal_job_for_internal_job_booking(linked_job_doc)
            if ls_name:
                linked_services_billed_via_operational_job.add(ls_name)
            linked_services_billed_via_operational_job.add((job_type, job_no))
            continue

        splits = list(
            iter_internal_job_charge_splits(
                job_type, job_no, customer=end_customer, prefer_actual=True
            )
        )
        if splits:
            ls_name = resolve_internal_job_for_internal_job_booking(linked_job_doc)
            if ls_name:
                linked_services_billed_via_operational_job.add(ls_name)
            linked_services_billed_via_operational_job.add((job_type, job_no))
        if not splits:
            continue

        for split in splits:
            rev = flt(split.get("revenue"))
            if rev <= 0:
                continue
            item_code = split.get("item_code")
            if not item_code:
                missing_item_codes.append("{0} {1}".format(job_type, job_no))
                continue
            _append_revenue_transfer_rows(
                entries,
                main_job_doc,
                linked_job_doc,
                rev,
                item_code,
                main_co,
                je_row_has_jcn,
            )

    for split in iter_main_job_linked_scope_charge_splits(main_job_doc):
        ls_name = split.get("linked_service")
        if not ls_name or ls_name in linked_services_billed_via_operational_job:
            continue
        if ls_name not in linked_job_doc_cache:
            op_jt, op_jn = resolve_operational_job_for_linked_service(
                ls_name,
                billing_main_type,
                billing_main_no,
                sales_quote_name=sales_quote_name,
            )
            if not op_jt or not op_jn:
                continue
            if (op_jt, op_jn) in linked_services_billed_via_operational_job:
                continue
            try:
                linked_job_doc_cache[ls_name] = frappe.get_doc(op_jt, op_jn)
            except Exception:
                continue
        linked_job_doc = linked_job_doc_cache[ls_name]
        op_co = getattr(linked_job_doc, "company", None)
        if not op_co or op_co != main_co:
            continue
        if _linked_job_internal_billing_already_posted(linked_job_doc, je_row_has_jcn):
            _note_already_billed(linked_job_doc)
            continue
        rev = flt(split.get("revenue"))
        if rev <= 0:
            continue
        item_code = split.get("item_code")
        if not item_code:
            missing_item_codes.append(
                _("Main Job {0} linked service {1}").format(billing_main_no, ls_name)
            )
            continue
        _append_revenue_transfer_rows(
            entries,
            main_job_doc,
            linked_job_doc,
            rev,
            item_code,
            main_co,
            je_row_has_jcn,
        )

    if missing_item_codes:
        return {
            "success": False,
            "created": 0,
            "message": _(
                "Internal billing requires item_code on charge lines. Missing on: {0}"
            ).format(", ".join(sorted(set(missing_item_codes)))),
        }

    if not entries:
        if already_billed:
            return {
                "success": True,
                "created": 0,
                "message": _("Internal billing already posted for linked jobs: {0}.").format(
                    ", ".join(already_billed)
                ),
            }
        return {
            "success": True,
            "created": 0,
            "message": _("No same-company linked jobs with revenue to bill."),
        }

    user_remark = _internal_billing_jv_user_remark(sales_quote_name, trigger_si)
    je_name = _submit_internal_billing_journal_entry(
        entries,
        main_co,
        posting_date,
        user_remark,
        sales_quote,
        end_customer,
        billing_main_job=main_job_doc,
    )

    return {
        "success": True,
        "created": 1,
        "journal_entry": je_name,
        "journal_entries": [je_name],
        "message": _("Created Internal Billing Journal Entry: {0}.").format(je_name),
    }


@frappe.whitelist()
def create_internal_billing_for_quote(
    sales_quote_name: str,
    posting_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Manually create internal billing Journal Entry for same-company linked jobs on this Sales Quote.
    """
    if not frappe.db.exists("Sales Quote", sales_quote_name):
        frappe.throw(_("Sales Quote {0} not found.").format(sales_quote_name))
    from logistics.utils.menu_permission import assert_perm

    assert_perm("Sales Quote", "write", doc=sales_quote_name)
    assert_perm("Journal Entry", "create")
    return create_internal_billing_journal_entries_for_quote(
        sales_quote_name=sales_quote_name,
        trigger_si=None,
        posting_date=posting_date or today(),
    )


LINKED_POSTING_ACTION_DOCTYPES = (
    "Transport Job",
    "Air Shipment",
    "Sea Shipment",
    "Declaration",
    "Docket",
)


def _charge_value(row, fieldname: str):
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get(fieldname)
    return getattr(row, fieldname, None)


def _doc_charges(doc) -> List[Any]:
    charges = doc.get("charges") if hasattr(doc, "get") else getattr(doc, "charges", None)
    return list(charges or [])


def _party_text(row: Any, fieldname: str) -> str:
    if not row:
        return ""
    if isinstance(row, dict):
        return (row.get(fieldname) or "").strip()
    return (getattr(row, fieldname, None) or "").strip()


def _represents_company(row: Any) -> str:
    return _party_text(row, "represents_company")


def _flag(row: Any, fieldname: str) -> int:
    if isinstance(row, dict):
        return cint(row.get(fieldname))
    return cint(getattr(row, fieldname, 0))


def _customer_kind(row: Any, company: str) -> str:
    """external, linked (another group company), or this_company."""
    if not row:
        return ""
    represents = _represents_company(row)
    internal = _flag(row, "is_internal_customer")
    if represents and company and represents == company:
        return "this_company"
    if internal and represents and represents != company:
        return "linked"
    if not internal:
        return "external"
    return ""


def _supplier_kind(row: Any, company: str) -> str:
    """outside, this_company, or other_company (internal supplier of another company)."""
    if not row:
        return ""
    represents = _represents_company(row)
    internal = _flag(row, "is_internal_supplier")
    if represents and company and represents == company:
        return "this_company"
    if internal and represents and represents != company:
        return "other_company"
    if not internal and not represents:
        return "outside"
    return ""


def _charge_parties(doc) -> tuple:
    """Distinct Bill To customers and Pay To suppliers. Cost rows have no Bill To."""
    bill_tos: List[str] = []
    pay_tos: List[str] = []
    seen_bill = set()
    seen_pay = set()
    for row in _doc_charges(doc):
        charge_type = (_charge_value(row, "charge_type") or "").strip()
        if charge_type != "Cost":
            bill_to = (_charge_value(row, "bill_to") or "").strip()
            if bill_to and bill_to not in seen_bill:
                seen_bill.add(bill_to)
                bill_tos.append(bill_to)
        pay_to = (_charge_value(row, "pay_to") or "").strip()
        if pay_to and pay_to not in seen_pay:
            seen_pay.add(pay_to)
            pay_tos.append(pay_to)
    return bill_tos, pay_tos


def _party_rows(doctype: str, names: List[str], fields: List[str]) -> Dict[str, Dict[str, Any]]:
    if not names:
        return {}
    rows = frappe.get_all(
        doctype,
        filters={"name": ["in", names]},
        fields=fields,
        ignore_permissions=True,
    )
    return {row.name: row for row in rows}


def _main_company_for_doc(doc) -> str:
    from logistics.billing.cross_module_billing import get_main_job_company
    from logistics.utils.service_role_rules import get_main_service_name, get_main_service_type

    company = get_main_job_company(get_main_service_type(doc), get_main_service_name(doc))
    return (company or "").strip()


def classify_linked_posting_actions(
    doc,
    customer_rows: Dict[str, Dict[str, Any]],
    supplier_rows: Optional[Dict[str, Dict[str, Any]]] = None,
    main_company: Optional[str] = None,
) -> Dict[str, bool]:
    """Which Create and Post invoice buttons this job should show.

    A button is on when any charge matches. Standalone jobs show Sales Invoice and
    Purchase Invoice. Main jobs follow Bill To and Pay To. Linked jobs show Purchase
    Invoice for an outside supplier, and Intercompany or Internal Billing when Bill To
    and Pay To represent group companies (an empty Pay To on that row counts as the
    group payee). The Linked split compares this job's company with the Main Job company.
    """
    from logistics.utils.service_role_rules import (
        SERVICE_ROLE_LINKED,
        SERVICE_ROLE_MAIN,
        SERVICE_ROLE_STANDALONE,
        get_service_role,
    )

    flags = {
        "sales_invoice": False,
        "purchase_invoice": False,
        "intercompany": False,
        "internal_billing": False,
    }
    role = get_service_role(doc)
    if role == SERVICE_ROLE_STANDALONE:
        flags["sales_invoice"] = True
        flags["purchase_invoice"] = True
        return flags
    if role not in (SERVICE_ROLE_MAIN, SERVICE_ROLE_LINKED):
        return flags

    supplier_rows = supplier_rows or {}
    company = (getattr(doc, "company", None) or "").strip()
    main_company = (main_company or "").strip()

    for row in _doc_charges(doc):
        charge_type = (_charge_value(row, "charge_type") or "").strip()
        bill_to = "" if charge_type == "Cost" else (_charge_value(row, "bill_to") or "").strip()
        pay_to = (_charge_value(row, "pay_to") or "").strip()
        customer = customer_rows.get(bill_to) if bill_to else None
        supplier = supplier_rows.get(pay_to) if pay_to else None

        if role == SERVICE_ROLE_MAIN:
            customer_kind = _customer_kind(customer, company)
            supplier_kind = _supplier_kind(supplier, company)
            if customer_kind == "linked":
                flags["intercompany"] = True
            if customer_kind == "external":
                flags["sales_invoice"] = True
            if supplier_kind == "outside":
                flags["purchase_invoice"] = True
            if supplier_kind == "other_company":
                flags["intercompany"] = True
            if supplier_kind == "this_company":
                flags["internal_billing"] = True
            continue

        supplier_kind = _supplier_kind(supplier, company)
        if supplier_kind == "outside":
            flags["purchase_invoice"] = True
            continue
        bill_is_group = bool(customer) and bool(_represents_company(customer))
        pay_is_group = (not pay_to) or bool(supplier and _represents_company(supplier))
        if not bill_is_group or not pay_is_group or not company or not main_company:
            continue
        if company != main_company:
            flags["intercompany"] = True
        else:
            flags["internal_billing"] = True
    return flags


@frappe.whitelist()
def get_linked_posting_actions(doctype: str, name: str) -> Dict[str, bool]:
    """Return which invoice buttons to show for this operational document."""
    if doctype not in LINKED_POSTING_ACTION_DOCTYPES:
        frappe.throw(_("Invalid document type: {0}").format(doctype))
    if not name or not frappe.db.exists(doctype, name):
        frappe.throw(_("{0} {1} does not exist.").format(doctype, name))
    from logistics.utils.menu_permission import assert_source_read

    doc = assert_source_read(doctype, name)
    bill_tos, pay_tos = _charge_parties(doc)
    return classify_linked_posting_actions(
        doc,
        _party_rows("Customer", bill_tos, ["name", "represents_company", "is_internal_customer"]),
        _party_rows("Supplier", pay_tos, ["name", "represents_company", "is_internal_supplier"]),
        _main_company_for_doc(doc),
    )
