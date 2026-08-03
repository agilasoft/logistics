# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Cross-module Job 360 query layer.

All Job Management dashboards, reports, number cards and notification helpers
delegate here so the cross-module joining logic lives in exactly one place. The
layer is keyed off ``Job Number`` and pulls operational details from the source
job DocType (Sea Shipment, Air Shipment, Transport Job, Warehouse Job,
Declaration, Special Project, Docket, Project Job, General Job) plus financial
roll-ups from GL / Sales Invoice / Purchase Invoice via the ``job_number``
accounting dimension.
"""

from __future__ import unicode_literals

from collections import OrderedDict, defaultdict
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, get_datetime, getdate, nowdate, today

from logistics.job_management.api import (
    get_job_profitability_from_gl,
    is_stock_received_not_billed_cost_account,
)
from logistics.job_management.logistics_job_status import ALLOWED_JOB_STATUS_VALUES


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Operational doctypes that can sit behind a Job Number. Order matters: it is
# used as the default ordering when grouping by job_type. New types can be
# added safely — every helper short-circuits if the doctype or field is absent.
JOB_TYPE_FIELD_MAP = OrderedDict([
    ("Sea Shipment", {
        "customer": "local_customer",
        "origin": "origin_port",
        "destination": "destination_port",
        "status": "job_status",
        "ops_status": "shipping_status",
        "etd": "etd",
        "eta": "eta",
        "mode": None,
        "vehicle_or_carrier": "shipping_line",
        "estimated_revenue": "estimated_revenue",
        "estimated_costs": "estimated_costs",
        "wip_amount": "wip_amount",
        "accrual_amount": "accrual_amount",
        "recognized_revenue": "recognized_revenue",
        "recognized_costs": "recognized_costs",
        "billing_status": "billing_status",
        "sla_status": "sla_status",
    }),
    ("Air Shipment", {
        "customer": "local_customer",
        "origin": "origin_port",
        "destination": "destination_port",
        "status": "job_status",
        # job_status is derived from the Air Shipment Milestone table.
        "ops_status": "job_status",
        "etd": "etd",
        "eta": "eta",
        "mode": "direction",
        "vehicle_or_carrier": "airline",
        "estimated_revenue": "estimated_revenue",
        "estimated_costs": "estimated_costs",
        "wip_amount": "wip_amount",
        "accrual_amount": "accrual_amount",
        "recognized_revenue": "recognized_revenue",
        "recognized_costs": "recognized_costs",
        "billing_status": "billing_status",
        "sla_status": "sla_status",
    }),
    ("Time Sensitive Case", {
        "customer": "customer",
        "origin": "origin",
        "destination": "destination",
        "status": "status",
        "ops_status": "status",
        "etd": None,
        "eta": "critical_deadline",
        "mode": "case_type",
        "vehicle_or_carrier": None,
        "estimated_revenue": None,
        "estimated_costs": None,
        "wip_amount": None,
        "accrual_amount": None,
        "recognized_revenue": None,
        "recognized_costs": None,
        "billing_status": "billing_status",
        "sla_status": "sla_status",
    }),
    ("Transport Job", {
        "customer": "customer",
        "origin": "origin",
        "destination": "destination",
        "status": "job_status",
        "ops_status": "sla_status",
        "etd": "scheduled_pickup",
        "eta": "scheduled_delivery",
        "mode": "transport_mode",
        "vehicle_or_carrier": "transport_company",
        "estimated_revenue": "estimated_revenue",
        "estimated_costs": "estimated_costs",
        "wip_amount": "wip_amount",
        "accrual_amount": "accrual_amount",
        "recognized_revenue": "recognized_revenue",
        "recognized_costs": "recognized_costs",
        "billing_status": "billing_status",
        "sla_status": "sla_status",
    }),
    ("Warehouse Job", {
        "customer": "customer",
        "origin": None,
        "destination": "warehouse",
        "status": "job_status",
        "ops_status": "sla_status",
        "etd": "job_open_date",
        "eta": "job_close_date",
        "mode": "type",
        "vehicle_or_carrier": None,
        "estimated_revenue": "estimated_revenue",
        "estimated_costs": "estimated_costs",
        "wip_amount": "wip_amount",
        "accrual_amount": "accrual_amount",
        "recognized_revenue": "recognized_revenue",
        "recognized_costs": "recognized_costs",
        "billing_status": "billing_status",
        "sla_status": "sla_status",
    }),
    ("Declaration", {
        "customer": "customer",
        "origin": "country_of_origin",
        "destination": "country_of_destination",
        "status": "job_status",
        "ops_status": "status",
        "etd": "declaration_date",
        "eta": "expected_clearance_date",
        "mode": "transport_mode",
        "vehicle_or_carrier": "customs_authority",
        "estimated_revenue": "estimated_revenue",
        "estimated_costs": "estimated_costs",
        "wip_amount": "wip_amount",
        "accrual_amount": "accrual_amount",
        "recognized_revenue": "recognized_revenue",
        "recognized_costs": "recognized_costs",
        "billing_status": "payment_status",
        "sla_status": "sla_status",
    }),
    ("Special Project", {
        "customer": "customer",
        "origin": None,
        "destination": None,
        "status": "status",
        "ops_status": "status",
        "etd": "planned_start",
        "eta": "planned_end",
        "mode": "project_type",
        "vehicle_or_carrier": None,
        "estimated_revenue": "estimated_revenue",
        "estimated_costs": "estimated_costs",
        "wip_amount": "wip_amount",
        "accrual_amount": "accrual_amount",
        "recognized_revenue": "recognized_revenue",
        "recognized_costs": "recognized_costs",
        "billing_status": "billing_status",
        "sla_status": None,
    }),
    ("Docket", {
        "customer": "customer",
        "origin": None,
        "destination": None,
        "status": "status",
        "ops_status": "status",
        "etd": None,
        "eta": None,
        "mode": None,
        "vehicle_or_carrier": None,
        "estimated_revenue": None,
        "estimated_costs": None,
        "wip_amount": None,
        "accrual_amount": None,
        "recognized_revenue": None,
        "recognized_costs": None,
        "billing_status": None,
        "sla_status": None,
    }),
    ("Project Job", {
        "customer": "customer",
        "origin": None,
        "destination": None,
        "status": "status",
        "ops_status": "status",
        "etd": None,
        "eta": None,
        "mode": None,
        "vehicle_or_carrier": None,
        "estimated_revenue": "estimated_revenue",
        "estimated_costs": "estimated_costs",
        "wip_amount": "wip_amount",
        "accrual_amount": "accrual_amount",
        "recognized_revenue": "recognized_revenue",
        "recognized_costs": "recognized_costs",
        "billing_status": None,
        "sla_status": None,
    }),
    ("General Job", {
        "customer": "customer",
        "origin": None,
        "destination": None,
        "status": "job_status",
        "ops_status": "job_status",
        "etd": None,
        "eta": None,
        "mode": None,
        "vehicle_or_carrier": None,
        "estimated_revenue": "estimated_revenue",
        "estimated_costs": "estimated_costs",
        "wip_amount": "wip_amount",
        "accrual_amount": "accrual_amount",
        "recognized_revenue": "recognized_revenue",
        "recognized_costs": "recognized_costs",
        "billing_status": None,
        "sla_status": None,
    }),
])


CLOSED_STATUS_TOKENS = frozenset({"Completed", "Closed", "Cancelled", "Cleared", "Released", "Delivered"})

DEFAULT_MARGIN_THRESHOLD = 10.0   # percent
DEFAULT_STALE_DAYS = 60           # for WIP / Accrual aging
DEFAULT_AR_OVERDUE_DAYS = 30


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_dict(filters):
    if not filters:
        return {}
    if isinstance(filters, str):
        try:
            import json as _json
            return _json.loads(filters) or {}
        except Exception:
            return {}
    if isinstance(filters, dict):
        return dict(filters)
    as_dict = getattr(filters, "as_dict", None)
    if callable(as_dict):
        try:
            return dict(as_dict())
        except Exception:
            pass
    try:
        return dict(filters)
    except Exception:
        return {}


def _meta_has_field(doctype, fieldname):
    if not doctype or not fieldname:
        return False
    try:
        return bool(frappe.get_meta(doctype).has_field(fieldname))
    except Exception:
        return False


def _aging_bucket(days):
    """Return one of '0-30', '31-60', '61-90', '91+'. Negative values bucket as '0-30'."""
    d = cint(days)
    if d <= 30:
        return "0-30"
    if d <= 60:
        return "31-60"
    if d <= 90:
        return "61-90"
    return "91+"


def _bucket_keys():
    return ["0-30", "31-60", "61-90", "91+"]


def _safe_field_list(doctype, fieldnames):
    """Return only field names that actually exist on the doctype (and 'name' is always added)."""
    if not doctype:
        return ["name"]
    out = ["name"]
    for fn in fieldnames or []:
        if fn and _meta_has_field(doctype, fn):
            out.append(fn)
    # Deduplicate preserving order
    seen = set()
    res = []
    for fn in out:
        if fn in seen:
            continue
        seen.add(fn)
        res.append(fn)
    return res


def _job_number_filters_from(filters):
    """Build a filters dict for tabJob Number from common scope filters."""
    f = _to_dict(filters)
    out = {"docstatus": ["<", 2]}
    if f.get("company"):
        out["company"] = f["company"]
    if f.get("branch"):
        out["branch"] = f["branch"]
    if f.get("cost_center"):
        out["cost_center"] = f["cost_center"]
    if f.get("profit_center"):
        out["profit_center"] = f["profit_center"]
    if f.get("job_type"):
        out["job_type"] = f["job_type"]
    if f.get("project"):
        out["project"] = f["project"]
    # Date scope on recognition_date OR job_open_date OR creation. We use creation
    # as the cap because it exists on every record. Dict filters expect a single
    # [operator, value] per field, so we use ``between`` whenever both bounds are
    # supplied, and otherwise fall back to ``>=`` / ``<=``.
    from_d = getdate(f["from_date"]) if f.get("from_date") else None
    to_d = getdate(f["to_date"]) if f.get("to_date") else None
    if from_d and to_d:
        out["creation"] = ["between", [from_d, to_d]]
    elif from_d:
        out["creation"] = [">=", from_d]
    elif to_d:
        out["creation"] = ["<=", to_d]
    return out


def _date_range_clause(filters, alias=None):
    """Return ('AND ...', values) clause for a SQL query on creation."""
    f = _to_dict(filters)
    parts = []
    values = {}
    prefix = (alias + ".") if alias else ""
    if f.get("from_date"):
        parts.append("{p}creation >= %(j360_from)s".format(p=prefix))
        values["j360_from"] = getdate(f["from_date"])
    if f.get("to_date"):
        parts.append("{p}creation <= %(j360_to)s".format(p=prefix))
        values["j360_to"] = getdate(f["to_date"])
    return (" AND ".join(parts)) if parts else "", values


def _scope_clause(filters, alias=None):
    """Return ('AND ...', values) clause for company/branch/cost_center/profit_center/job_type."""
    f = _to_dict(filters)
    parts = []
    values = {}
    prefix = (alias + ".") if alias else ""
    if f.get("company"):
        parts.append("{p}company = %(j360_company)s".format(p=prefix))
        values["j360_company"] = f["company"]
    if f.get("branch"):
        parts.append("{p}branch = %(j360_branch)s".format(p=prefix))
        values["j360_branch"] = f["branch"]
    if f.get("cost_center"):
        parts.append("{p}cost_center = %(j360_cc)s".format(p=prefix))
        values["j360_cc"] = f["cost_center"]
    if f.get("profit_center"):
        parts.append("{p}profit_center = %(j360_pc)s".format(p=prefix))
        values["j360_pc"] = f["profit_center"]
    if f.get("job_type"):
        parts.append("{p}job_type = %(j360_jt)s".format(p=prefix))
        values["j360_jt"] = f["job_type"]
    if f.get("project"):
        parts.append("{p}project = %(j360_proj)s".format(p=prefix))
        values["j360_proj"] = f["project"]
    return (" AND ".join(parts)) if parts else "", values


# ---------------------------------------------------------------------------
# Source-doc resolution
# ---------------------------------------------------------------------------

def _fetch_source_docs(job_type, job_names):
    """Bulk-fetch source DocType rows for a set of job_no values."""
    if not job_type or not job_names:
        return {}
    if not frappe.db.exists("DocType", job_type):
        return {}

    spec = JOB_TYPE_FIELD_MAP.get(job_type, {})
    candidate_fields = [v for v in spec.values() if v]
    candidate_fields += ["customer", "company"]

    fields = _safe_field_list(job_type, candidate_fields)

    try:
        rows = frappe.get_all(
            job_type,
            filters={"name": ["in", list({n for n in job_names if n})]},
            fields=fields,
            ignore_permissions=False,
            limit_page_length=0,
        )
    except Exception:
        # Fall back to a per-name fetch if the bulk call fails for any reason.
        frappe.log_error(frappe.get_traceback(), "job_360._fetch_source_docs:{0}".format(job_type))
        rows = []
        for name in job_names:
            try:
                rows.append(frappe.db.get_value(job_type, name, fields, as_dict=True) or {"name": name})
            except Exception:
                continue
    return {(r.get("name") or ""): r for r in rows}


def _operational_row(job_type, source_doc):
    """Project the source doc into a normalized row used by Job 360."""
    spec = JOB_TYPE_FIELD_MAP.get(job_type) or {}
    out = {
        "customer": None,
        "origin": None,
        "destination": None,
        "ops_status": None,
        "etd": None,
        "eta": None,
        "mode": None,
        "vehicle_or_carrier": None,
        "estimated_revenue": 0.0,
        "estimated_costs": 0.0,
        "wip_amount_doc": 0.0,
        "accrual_amount_doc": 0.0,
        "recognized_revenue": 0.0,
        "recognized_costs": 0.0,
        "billing_status": None,
        "sla_status": None,
    }
    if not source_doc:
        return out
    for key, source_field in spec.items():
        if not source_field:
            continue
        val = source_doc.get(source_field)
        if key in ("estimated_revenue", "estimated_costs", "recognized_revenue", "recognized_costs"):
            out[key] = flt(val)
        elif key == "wip_amount":
            out["wip_amount_doc"] = flt(val)
        elif key == "accrual_amount":
            out["accrual_amount_doc"] = flt(val)
        elif key == "status":
            if not out.get("ops_status"):
                out["ops_status"] = val
        else:
            out[key] = val
    return out


def _normalize_status(value):
    if value is None:
        return None
    sval = str(value).strip()
    if not sval:
        return None
    if sval in ALLOWED_JOB_STATUS_VALUES:
        return sval
    return sval


# ---------------------------------------------------------------------------
# Receivables / Payables (Sales Invoice / Purchase Invoice)
# ---------------------------------------------------------------------------

def _invoice_has_job_number(invoice_doctype):
    return _meta_has_field(invoice_doctype, "job_number")


def _ar_ap_query(doctype, filters, only_outstanding=True):
    """Return invoice rows tagged with job_number under the current scope."""
    if not _invoice_has_job_number(doctype):
        return []
    f = _to_dict(filters)

    where = ["docstatus = 1", "IFNULL(job_number, '') != ''"]
    values = {}
    if f.get("company"):
        where.append("company = %(company)s")
        values["company"] = f["company"]
    if f.get("from_date"):
        where.append("posting_date >= %(from_date)s")
        values["from_date"] = getdate(f["from_date"])
    if f.get("to_date"):
        where.append("posting_date <= %(to_date)s")
        values["to_date"] = getdate(f["to_date"])
    if only_outstanding:
        where.append("outstanding_amount > 0")
    if f.get("job_number"):
        where.append("job_number = %(job_number)s")
        values["job_number"] = f["job_number"]
    if f.get("customer") and doctype == "Sales Invoice":
        where.append("customer = %(customer)s")
        values["customer"] = f["customer"]
    if f.get("supplier") and doctype == "Purchase Invoice":
        where.append("supplier = %(supplier)s")
        values["supplier"] = f["supplier"]

    where_sql = " AND ".join(where)

    if doctype == "Sales Invoice":
        party_col = "customer AS party, customer_name AS party_name"
    else:
        party_col = "supplier AS party, supplier_name AS party_name"

    rows = frappe.db.sql(
        """
        SELECT
            name AS invoice,
            job_number,
            company,
            posting_date,
            due_date,
            grand_total,
            outstanding_amount,
            currency,
            {party_col}
        FROM `tab{doctype}`
        WHERE {where}
        ORDER BY posting_date DESC, name DESC
        """.format(party_col=party_col, doctype=doctype, where=where_sql),
        values,
        as_dict=True,
    )
    today_d = getdate(today())
    for r in rows:
        due = r.get("due_date") or r.get("posting_date")
        days = date_diff(today_d, getdate(due)) if due else 0
        r["days_overdue"] = max(0, days)
        r["age_bucket"] = _aging_bucket(days)
    return rows


def get_jobs_ar(filters=None, only_outstanding=True):
    """Per-Sales-Invoice AR rows tagged with job_number."""
    return _ar_ap_query("Sales Invoice", filters, only_outstanding=only_outstanding)


def get_jobs_ap(filters=None, only_outstanding=True):
    """Per-Purchase-Invoice AP rows tagged with job_number."""
    return _ar_ap_query("Purchase Invoice", filters, only_outstanding=only_outstanding)


def _aging_summary(rows):
    """Roll up per-job aging buckets from get_jobs_ar/ap rows."""
    out = defaultdict(lambda: {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "91+": 0.0, "total": 0.0, "invoice_count": 0})
    for r in rows:
        bucket = r.get("age_bucket") or _aging_bucket(r.get("days_overdue", 0))
        amt = flt(r.get("outstanding_amount"))
        jn = r.get("job_number")
        if not jn:
            continue
        out[jn][bucket] += amt
        out[jn]["total"] += amt
        out[jn]["invoice_count"] += 1
    return out


# ---------------------------------------------------------------------------
# Bulk GL roll-up (avoids per-job N+1)
# ---------------------------------------------------------------------------

def _gl_has_job_number_column():
    try:
        return frappe.db.has_column("GL Entry", "job_number")
    except Exception:
        return False


def _bulk_gl_rollup(filters=None, job_names=None):
    """One-shot GL aggregation by job_number.

    Returns a dict ``{job_number: {revenue, cost, wip, accrual, disbursements,
    gross_profit, profit_margin_pct}}``. The classification mirrors the per-job
    helper in [api.py](api.py) but uses ``job_profit_account_type`` (account
    classification) instead of per-job policy-account lookups, which is both
    accurate and fast for dashboard roll-ups across thousands of jobs.

    Returns an empty dict if the ``job_number`` accounting dimension column
    has not yet been created on ``tab GL Entry`` (so the dashboards stay
    safe on freshly bootstrapped sites).
    """
    if not _gl_has_job_number_column():
        return {}

    f = _to_dict(filters)

    where = [
        "gle.docstatus = 1",
        "IFNULL(gle.job_number, '') != ''",
    ]
    values = {}
    if f.get("company"):
        where.append("gle.company = %(company)s")
        values["company"] = f["company"]
    if f.get("from_date"):
        where.append("gle.posting_date >= %(from_date)s")
        values["from_date"] = getdate(f["from_date"])
    if f.get("to_date"):
        where.append("gle.posting_date <= %(to_date)s")
        values["to_date"] = getdate(f["to_date"])
    if job_names:
        # Limit to a known set of job numbers (very large IN lists are still fine
        # for MariaDB; we cap at 5000 just in case).
        names = list({n for n in job_names if n})[:5000]
        if not names:
            return {}
        placeholders = ", ".join(["%s"] * len(names))
        where.append("gle.job_number IN ({0})".format(placeholders))
        sql_args = list(values.values()) + names
        # Fall back to positional args when we have an IN clause
        params_kind = "positional"
    else:
        sql_args = values
        params_kind = "named"

    has_jp = False
    try:
        has_jp = frappe.db.has_column("Account", "job_profit_account_type")
    except Exception:
        has_jp = False
    jpat_select = "IFNULL(acc.job_profit_account_type, '')" if has_jp else "''"

    sql = """
        SELECT
            gle.job_number AS job_number,
            acc.root_type AS root_type,
            acc.account_type AS account_type,
            {jpat_sel} AS jpat,
            SUM(gle.debit) AS sum_debit,
            SUM(gle.credit) AS sum_credit
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE {where}
        GROUP BY gle.job_number, acc.root_type, acc.account_type, {jpat_sel}
    """.format(jpat_sel=jpat_select, where=" AND ".join(where))

    if params_kind == "named":
        # Need to use positional placeholders since we mixed IN clause; rebuild
        # for the named case by replacing %(x)s with values inline through a
        # second sql() call. Simpler: just use the named dict directly.
        rows = frappe.db.sql(sql, values, as_dict=True)
    else:
        # Convert %(name)s placeholders to positional %s in order
        ordered = []
        positional_sql = sql
        for k in list(values.keys()):
            positional_sql = positional_sql.replace("%({0})s".format(k), "%s", 1)
            ordered.append(values[k])
        positional_sql_args = ordered + names
        rows = frappe.db.sql(positional_sql, positional_sql_args, as_dict=True)

    out = defaultdict(lambda: {
        "revenue": 0.0,
        "cost": 0.0,
        "wip_amount": 0.0,
        "accrual_amount": 0.0,
        "disbursements_amount": 0.0,
        "gross_profit": 0.0,
        "profit_margin_pct": 0.0,
    })

    for r in rows:
        jn = r.get("job_number")
        if not jn:
            continue
        rt = (r.get("root_type") or "").strip()
        account_type = (r.get("account_type") or "").strip()
        jpat = (r.get("jpat") or "").strip()
        sum_debit = flt(r.get("sum_debit"))
        sum_credit = flt(r.get("sum_credit"))
        bucket = out[jn]

        if jpat == "Disbursements":
            if rt == "Income":
                bucket["disbursements_amount"] += sum_credit - sum_debit
            elif rt in ("Expense",):
                bucket["disbursements_amount"] += sum_debit - sum_credit
            elif rt == "Liability":
                bucket["disbursements_amount"] += sum_credit - sum_debit
            else:
                bucket["disbursements_amount"] += sum_debit - sum_credit
        elif jpat == "WIP":
            if rt == "Income":
                bucket["wip_amount"] += sum_credit - sum_debit
            elif rt == "Asset":
                bucket["wip_amount"] += sum_debit - sum_credit
            else:
                bucket["wip_amount"] += sum_credit - sum_debit
        elif jpat == "Accrual":
            if rt == "Liability":
                bucket["accrual_amount"] += sum_credit - sum_debit
            elif rt == "Expense":
                bucket["accrual_amount"] += sum_debit - sum_credit
            else:
                bucket["accrual_amount"] += sum_credit - sum_debit
        elif rt == "Income":
            bucket["revenue"] += sum_credit - sum_debit
        elif rt == "Expense":
            bucket["cost"] += sum_debit - sum_credit
        elif is_stock_received_not_billed_cost_account(rt, account_type):
            bucket["cost"] += sum_debit - sum_credit

    for jn, b in out.items():
        gp = flt(b["revenue"]) - flt(b["cost"])
        b["gross_profit"] = gp
        b["profit_margin_pct"] = (gp / b["revenue"] * 100.0) if b["revenue"] else 0.0
        for k in ("revenue", "cost", "wip_amount", "accrual_amount", "disbursements_amount", "gross_profit"):
            b[k] = flt(b[k], 2)
        b["profit_margin_pct"] = flt(b["profit_margin_pct"], 2)

    return dict(out)


def get_jobs_ar_summary(filters=None):
    return _aging_summary(get_jobs_ar(filters))


def get_jobs_ap_summary(filters=None):
    return _aging_summary(get_jobs_ap(filters))


# ---------------------------------------------------------------------------
# GL-based job financials and recognition aging
# ---------------------------------------------------------------------------

def _policy_accounts_for(job_name):
    """Return (wip_account, accrued_cost_liability_account, cost_accrual_account) for a job."""
    try:
        from logistics.job_management.recognition_engine import get_recognition_policy_for_job

        policy = get_recognition_policy_for_job(job_name)
    except Exception:
        policy = None
    if not policy:
        return (None, None, None)
    return (
        policy.get("wip_account"),
        policy.get("accrued_cost_liability_account"),
        policy.get("cost_accrual_account"),
    )


def _gl_account_oldest(job_name, company, account, sign="cr_minus_dr"):
    """Open balance and oldest entry date for a GL account, scoped to a job_number."""
    if not (job_name and company and account):
        return (0.0, None)
    if sign == "cr_minus_dr":
        amount_expr = "SUM(credit - debit)"
    else:
        amount_expr = "SUM(debit - credit)"
    rows = frappe.db.sql(
        """
        SELECT
            COALESCE({amt}, 0) AS balance,
            MIN(posting_date) AS earliest
        FROM `tabGL Entry`
        WHERE job_number = %(jn)s
          AND company = %(co)s
          AND account = %(acc)s
          AND docstatus = 1
        """.format(amt=amount_expr),
        {"jn": job_name, "co": company, "acc": account},
        as_dict=True,
    )
    if not rows:
        return (0.0, None)
    return (flt(rows[0].balance), rows[0].earliest)


def get_recognition_aging(filters=None):
    """Per-Job WIP and Accrual aging, including stale flag."""
    f = _to_dict(filters)
    stale_days = cint(f.get("stale_days") or DEFAULT_STALE_DAYS)
    today_d = getdate(today())

    jn_filters = _job_number_filters_from(f)
    jn_filters.pop("creation", None)  # aging is independent of recognition_date scope

    job_rows = frappe.get_all(
        "Job Number",
        filters=jn_filters,
        fields=["name", "job_type", "job_no", "company", "branch", "cost_center", "profit_center", "recognition_date", "job_open_date"],
        limit_page_length=0,
    )
    out = []
    for jn in job_rows:
        wip_acc, accr_liab, cost_accr = _policy_accounts_for(jn.name)
        wip_balance, wip_oldest = _gl_account_oldest(jn.name, jn.company, wip_acc, sign="cr_minus_dr")
        if accr_liab:
            accr_balance, accr_oldest = _gl_account_oldest(jn.name, jn.company, accr_liab, sign="cr_minus_dr")
        else:
            accr_balance, accr_oldest = _gl_account_oldest(jn.name, jn.company, cost_accr, sign="dr_minus_cr")

        wip_age = date_diff(today_d, getdate(wip_oldest)) if wip_oldest else 0
        accr_age = date_diff(today_d, getdate(accr_oldest)) if accr_oldest else 0

        if abs(flt(wip_balance)) < 0.01 and abs(flt(accr_balance)) < 0.01:
            continue

        out.append({
            "job_number": jn.name,
            "job_type": jn.job_type,
            "job_no": jn.job_no,
            "company": jn.company,
            "branch": jn.branch,
            "cost_center": jn.cost_center,
            "profit_center": jn.profit_center,
            "wip_account": wip_acc,
            "wip_balance": flt(wip_balance, 2),
            "wip_oldest_date": wip_oldest,
            "wip_age_days": cint(wip_age),
            "wip_aging_bucket": _aging_bucket(wip_age) if abs(flt(wip_balance)) >= 0.01 else None,
            "wip_stale": bool(abs(flt(wip_balance)) >= 0.01 and wip_age > stale_days),
            "accrual_account": accr_liab or cost_accr,
            "accrual_balance": flt(accr_balance, 2),
            "accrual_oldest_date": accr_oldest,
            "accrual_age_days": cint(accr_age),
            "accrual_aging_bucket": _aging_bucket(accr_age) if abs(flt(accr_balance)) >= 0.01 else None,
            "accrual_stale": bool(abs(flt(accr_balance)) >= 0.01 and accr_age > stale_days),
        })
    out.sort(key=lambda r: max(r["wip_age_days"], r["accrual_age_days"]), reverse=True)
    return out


# ---------------------------------------------------------------------------
# Status pipeline
# ---------------------------------------------------------------------------

def get_job_status_pipeline(filters=None):
    """Return [{job_type, status, count, value}] across all configured operational doctypes."""
    f = _to_dict(filters)
    out = []

    jn_filters = _job_number_filters_from(f)
    jn_filters.pop("creation", None)
    jn_rows = frappe.get_all(
        "Job Number",
        filters=jn_filters,
        fields=["name", "job_type", "job_no"],
        limit_page_length=0,
    )

    by_type = defaultdict(list)
    for r in jn_rows:
        if r.get("job_type") and r.get("job_no"):
            by_type[r["job_type"]].append(r["job_no"])

    for job_type, names in by_type.items():
        if job_type not in JOB_TYPE_FIELD_MAP:
            continue
        spec = JOB_TYPE_FIELD_MAP[job_type]
        status_field = spec.get("status") or "job_status"
        if not _meta_has_field(job_type, status_field):
            continue
        amount_field = spec.get("estimated_revenue") if _meta_has_field(job_type, spec.get("estimated_revenue") or "") else None
        try:
            fields = ["name", status_field]
            if amount_field:
                fields.append(amount_field)
            rows = frappe.get_all(
                job_type,
                filters={"name": ["in", names]},
                fields=fields,
                limit_page_length=0,
            )
        except Exception:
            continue
        agg = defaultdict(lambda: {"count": 0, "value": 0.0})
        for row in rows:
            status = (row.get(status_field) or "Unknown").strip() or "Unknown"
            agg[status]["count"] += 1
            if amount_field:
                agg[status]["value"] += flt(row.get(amount_field))
        for status, vals in agg.items():
            out.append({
                "job_type": job_type,
                "status": status,
                "count": cint(vals["count"]),
                "value": flt(vals["value"], 2),
            })
    out.sort(key=lambda r: (r["job_type"], -r["count"]))
    return out


# ---------------------------------------------------------------------------
# Document alerts roll-up
# ---------------------------------------------------------------------------

def _get_document_alerts_safe(job_type, job_name):
    try:
        from logistics.document_management.api import get_document_alerts

        alerts = get_document_alerts(job_type, job_name) or {}
        counts = alerts.get("counts") or {}
        return {
            "missing": cint(counts.get("pending")),
            "overdue": cint(counts.get("overdue")),
            "expiring_soon": cint(counts.get("expiring_soon")),
            "received": cint(counts.get("received")),
            "total": cint(counts.get("total")),
        }
    except Exception:
        return {"missing": 0, "overdue": 0, "expiring_soon": 0, "received": 0, "total": 0}


def _bulk_document_alerts(jn_rows):
    """Bulk roll-up for the ``Job Document`` child table across all parents.

    Replaces the per-parent ``frappe.get_doc`` loop with a single SQL query
    over ``tabJob Document`` grouped by ``parenttype`` + ``parent``. Returns
    a dict ``{job_number_name: counts_dict}``.
    """
    empty = {"missing": 0, "overdue": 0, "expiring_soon": 0, "received": 0, "total": 0}
    if not jn_rows:
        return {}

    parents_by_type = defaultdict(set)
    parent_to_job = {}
    for jn in jn_rows:
        jt = jn.get("job_type") or ""
        jno = jn.get("job_no") or ""
        if not jt or not jno:
            continue
        parents_by_type[jt].add(jno)
        parent_to_job[(jt, jno)] = jn["name"]

    if not parents_by_type:
        return {}

    out = {jn["name"]: dict(empty) for jn in jn_rows}

    if not _meta_has_field("Job Document", "is_required"):
        return out

    today_d = getdate(today())
    soon = today_d + timedelta(days=7)

    has_expiry = _meta_has_field("Job Document", "expiry_date")

    for parenttype, parents in parents_by_type.items():
        names = list(parents)
        if not names:
            continue
        ph = ", ".join(["%s"] * len(names))
        cols = "name, parent, status, date_required, is_required"
        if has_expiry:
            cols += ", expiry_date"
        rows = frappe.db.sql(
            f"""
            SELECT {cols}
            FROM `tabJob Document`
            WHERE parenttype = %s
              AND parent IN ({ph})
            """,
            [parenttype, *names],
            as_dict=True,
        )
        for r in rows:
            jn_name = parent_to_job.get((parenttype, r.get("parent")))
            if not jn_name:
                continue
            bucket = out[jn_name]
            bucket["total"] += 1
            status = (r.get("status") or "").strip()
            if status in ("Received", "Verified", "Done"):
                bucket["received"] += 1
                # Even when received, surface upcoming expirations
                if has_expiry and r.get("expiry_date"):
                    exp = getdate(r.get("expiry_date"))
                    if exp <= soon:
                        bucket["expiring_soon"] += 1
                continue
            if not r.get("is_required"):
                continue
            dr = r.get("date_required")
            if dr:
                drd = getdate(dr)
                if drd < today_d:
                    bucket["overdue"] += 1
                else:
                    bucket["missing"] += 1
            else:
                bucket["missing"] += 1
    return out


def get_alerts_summary(filters=None, jn_rows=None):
    """Per-Job alerts roll-up. Pass jn_rows to avoid double queries."""
    f = _to_dict(filters)
    if jn_rows is None:
        jn_filters = _job_number_filters_from(f)
        jn_rows = frappe.get_all(
            "Job Number",
            filters=jn_filters,
            fields=["name", "job_type", "job_no"],
            limit_page_length=0,
        )
    return _bulk_document_alerts(jn_rows)


# ---------------------------------------------------------------------------
# Master 360 row builder
# ---------------------------------------------------------------------------

def get_job_360_rows(filters=None, include_alerts=True, include_gl=True, limit=None, offset=None):
    """One row per Job Number with operational + financial + AR/AP + alerts data.

    The GL roll-up is computed in a single bulk SQL aggregation
    (`_bulk_gl_rollup`) rather than per-job, so this scales to thousands of
    jobs without N+1 query storms. Set ``include_gl=False`` to skip it
    altogether (useful for purely operational reports). Set
    ``include_alerts=False`` to skip the per-job document-alerts loop, which
    is the most expensive remaining step.
    """
    f = _to_dict(filters)

    jn_filters = _job_number_filters_from(f)
    jn_fields = [
        "name", "job_type", "job_no", "company", "branch", "cost_center",
        "profit_center", "project", "docket", "recognition_date", "job_open_date",
        "creation", "modified", "owner", "docstatus",
    ]
    jn_rows = frappe.get_all(
        "Job Number",
        filters=jn_filters,
        fields=jn_fields,
        order_by="recognition_date desc, creation desc",
        limit_start=cint(offset) if offset else 0,
        limit_page_length=cint(limit) if limit else 0,
    )

    by_type = defaultdict(list)
    for r in jn_rows:
        if r.get("job_type") and r.get("job_no"):
            by_type[r["job_type"]].append(r["job_no"])

    source_doc_index = {}
    for job_type, names in by_type.items():
        source_doc_index[job_type] = _fetch_source_docs(job_type, names)

    ar_summary = get_jobs_ar_summary(f)
    ap_summary = get_jobs_ap_summary(f)
    alerts_index = get_alerts_summary(f, jn_rows=jn_rows) if include_alerts else {}

    # Bulk GL roll-up - one SQL grouped by job_number
    gl_index = {}
    if include_gl:
        try:
            gl_index = _bulk_gl_rollup(
                filters=f,
                job_names=[r["name"] for r in jn_rows],
            )
        except Exception:
            frappe.log_error(frappe.get_traceback(), "job_360._bulk_gl_rollup")
            gl_index = {}

    def _empty_aging():
        return {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "91+": 0.0, "total": 0.0, "invoice_count": 0}

    def _empty_gl():
        return {
            "revenue": 0.0, "cost": 0.0, "gross_profit": 0.0,
            "profit_margin_pct": 0.0, "wip_amount": 0.0, "accrual_amount": 0.0,
            "disbursements_amount": 0.0,
        }

    out = []
    for jn in jn_rows:
        source_doc = (source_doc_index.get(jn.get("job_type") or "") or {}).get(jn.get("job_no") or "") or {}
        ops = _operational_row(jn.get("job_type"), source_doc)

        prof = gl_index.get(jn["name"]) or _empty_gl()
        prof.setdefault("currency", None)

        ar = ar_summary.get(jn["name"], _empty_aging())
        ap = ap_summary.get(jn["name"], _empty_aging())
        alerts = alerts_index.get(jn["name"], {"missing": 0, "overdue": 0, "expiring_soon": 0, "received": 0, "total": 0})

        est_rev = flt(ops.get("estimated_revenue"))
        est_cost = flt(ops.get("estimated_costs"))
        gl_rev = flt(prof.get("revenue"))
        gl_cost = flt(prof.get("cost"))
        gp = flt(prof.get("gross_profit"))
        margin_pct = flt(prof.get("profit_margin_pct"))

        out.append({
            "job_number": jn["name"],
            "job_type": jn.get("job_type"),
            "job_no": jn.get("job_no"),
            "company": jn.get("company"),
            "branch": jn.get("branch"),
            "cost_center": jn.get("cost_center"),
            "profit_center": jn.get("profit_center"),
            "project": jn.get("project"),
            "docket": jn.get("docket"),
            "recognition_date": jn.get("recognition_date"),
            "job_open_date": jn.get("job_open_date"),
            "creation": jn.get("creation"),
            "owner": jn.get("owner"),
            "docstatus": jn.get("docstatus"),

            "customer": ops.get("customer"),
            "origin": ops.get("origin"),
            "destination": ops.get("destination"),
            "ops_status": ops.get("ops_status"),
            "etd": ops.get("etd"),
            "eta": ops.get("eta"),
            "mode": ops.get("mode"),
            "vehicle_or_carrier": ops.get("vehicle_or_carrier"),
            "billing_status": ops.get("billing_status"),
            "sla_status": ops.get("sla_status"),

            "estimated_revenue": est_rev,
            "estimated_costs": est_cost,
            "wip_amount_doc": flt(ops.get("wip_amount_doc")),
            "accrual_amount_doc": flt(ops.get("accrual_amount_doc")),
            "recognized_revenue": flt(ops.get("recognized_revenue")),
            "recognized_costs": flt(ops.get("recognized_costs")),

            "gl_revenue": flt(gl_rev, 2),
            "gl_cost": flt(gl_cost, 2),
            "gross_profit": flt(gp, 2),
            "profit_margin_pct": flt(margin_pct, 2),
            "wip_amount": flt(prof.get("wip_amount"), 2),
            "accrual_amount": flt(prof.get("accrual_amount"), 2),
            "disbursements_amount": flt(prof.get("disbursements_amount"), 2),
            "currency": prof.get("currency"),

            "ar_outstanding": flt(ar.get("total"), 2),
            "ar_0_30": flt(ar.get("0-30"), 2),
            "ar_31_60": flt(ar.get("31-60"), 2),
            "ar_61_90": flt(ar.get("61-90"), 2),
            "ar_91_plus": flt(ar.get("91+"), 2),
            "ar_invoice_count": cint(ar.get("invoice_count")),

            "ap_outstanding": flt(ap.get("total"), 2),
            "ap_0_30": flt(ap.get("0-30"), 2),
            "ap_31_60": flt(ap.get("31-60"), 2),
            "ap_61_90": flt(ap.get("61-90"), 2),
            "ap_91_plus": flt(ap.get("91+"), 2),
            "ap_invoice_count": cint(ap.get("invoice_count")),

            "alerts_missing": cint(alerts.get("missing")),
            "alerts_overdue": cint(alerts.get("overdue")),
            "alerts_expiring": cint(alerts.get("expiring_soon")),
            "alerts_total": cint(alerts.get("total")),

            "billed_value": flt(ar.get("total"), 2) + flt(prof.get("revenue"), 2),
            "billing_gap": flt(est_rev - gl_rev, 2),
        })
    return out


@frappe.whitelist()
def get_dashboard_kpis(filters=None):
    """Return aggregate KPIs for the Job 360 explorer page header tiles."""
    rows = get_job_360_rows(filters=filters, include_alerts=False, include_gl=True)
    margin_threshold = flt(_to_dict(filters).get("margin_threshold") or DEFAULT_MARGIN_THRESHOLD)
    return _aggregate_kpis(rows, margin_threshold=margin_threshold)


@frappe.whitelist()
def get_job_360_table(filters=None, limit=50, offset=0, include_alerts=False):
    """Paginated rows for the Job 360 explorer page table.

    Alerts are off by default to keep the call fast — the explorer renders
    aggregated counts via ``get_alerts_summary`` only on the visible page.
    """
    if isinstance(include_alerts, str):
        include_alerts = include_alerts.lower() not in ("0", "false", "")
    return get_job_360_rows(
        filters=filters,
        include_alerts=bool(include_alerts),
        include_gl=True,
        limit=cint(limit) or 50,
        offset=cint(offset) or 0,
    )


@frappe.whitelist()
def get_job_360_payload(filters=None, limit=50, offset=0):
    """One-shot payload for the explorer page: kpis + chart data + table rows.

    Single backend round-trip and a single ``get_job_360_rows`` invocation:
    the full filtered set is built once, KPIs and chart buckets are
    aggregated server-side, and only the requested page slice is shipped to
    the browser.
    """
    f = _to_dict(filters)
    page_limit = cint(limit) or 50
    page_offset = cint(offset) or 0

    full_rows = get_job_360_rows(
        filters=f,
        include_alerts=False,
        include_gl=True,
    )
    kpis = _aggregate_kpis(full_rows, margin_threshold=flt(f.get("margin_threshold") or DEFAULT_MARGIN_THRESHOLD))
    pipeline = get_job_status_pipeline(f)

    type_buckets = defaultdict(int)
    status_buckets = defaultdict(int)
    ar_buckets = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "91+": 0.0}
    ap_buckets = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "91+": 0.0}
    for r in full_rows:
        type_buckets[r.get("job_type") or "Unknown"] += 1
        status_buckets[r.get("ops_status") or "Unknown"] += 1
        ar_buckets["0-30"] += flt(r.get("ar_0_30"))
        ar_buckets["31-60"] += flt(r.get("ar_31_60"))
        ar_buckets["61-90"] += flt(r.get("ar_61_90"))
        ar_buckets["91+"] += flt(r.get("ar_91_plus"))
        ap_buckets["0-30"] += flt(r.get("ap_0_30"))
        ap_buckets["31-60"] += flt(r.get("ap_31_60"))
        ap_buckets["61-90"] += flt(r.get("ap_61_90"))
        ap_buckets["91+"] += flt(r.get("ap_91_plus"))

    page_rows = full_rows[page_offset:page_offset + page_limit]

    return {
        "kpis": kpis,
        "rows": page_rows,
        "row_count": len(full_rows),
        "page_offset": page_offset,
        "page_limit": page_limit,
        "charts": {
            "by_type": [{"label": k, "value": v} for k, v in sorted(type_buckets.items(), key=lambda x: -x[1])][:12],
            "by_status": [{"label": k, "value": v} for k, v in sorted(status_buckets.items(), key=lambda x: -x[1])][:12],
            "ar_aging": [{"label": k, "value": flt(v, 2)} for k, v in ar_buckets.items()],
            "ap_aging": [{"label": k, "value": flt(v, 2)} for k, v in ap_buckets.items()],
        },
        "pipeline": pipeline,
    }


def _aggregate_kpis(rows, margin_threshold=DEFAULT_MARGIN_THRESHOLD):
    open_jobs = 0
    at_risk = 0
    revenue_total = 0.0
    cost_total = 0.0
    gp_total = 0.0
    wip_total = 0.0
    accrual_total = 0.0
    ar_total = 0.0
    ap_total = 0.0
    for r in rows:
        status = (r.get("ops_status") or "").strip()
        if status not in CLOSED_STATUS_TOKENS:
            open_jobs += 1
        revenue_total += flt(r.get("gl_revenue") or r.get("revenue"))
        cost_total += flt(r.get("gl_cost") or r.get("cost"))
        gp_total += flt(r.get("gross_profit"))
        wip_total += flt(r.get("wip_amount"))
        accrual_total += flt(r.get("accrual_amount"))
        ar_total += flt(r.get("ar_outstanding"))
        ap_total += flt(r.get("ap_outstanding"))
        if (
            flt(r.get("gross_profit")) < 0
            or (flt(r.get("gl_revenue") or r.get("revenue")) > 0 and flt(r.get("profit_margin_pct")) < margin_threshold)
            or flt(r.get("ar_91_plus")) > 0
        ):
            at_risk += 1
    margin_pct_total = (gp_total / revenue_total * 100.0) if revenue_total else 0.0
    return {
        "open_jobs": open_jobs,
        "at_risk_jobs": at_risk,
        "total_jobs": len(rows),
        "revenue": flt(revenue_total, 2),
        "cost": flt(cost_total, 2),
        "gross_profit": flt(gp_total, 2),
        "margin_pct": flt(margin_pct_total, 2),
        "wip": flt(wip_total, 2),
        "accrual": flt(accrual_total, 2),
        "ar_outstanding": flt(ar_total, 2),
        "ap_outstanding": flt(ap_total, 2),
    }


@frappe.whitelist()
def get_job_status_pipeline_api(filters=None):
    return get_job_status_pipeline(filters)


@frappe.whitelist()
def get_recognition_aging_api(filters=None):
    return get_recognition_aging(filters)


# ---------------------------------------------------------------------------
# Notification helpers
# ---------------------------------------------------------------------------

def get_jobs_below_margin(filters=None):
    """Return jobs whose margin% is below the configured threshold (or GP < 0)."""
    f = _to_dict(filters or {})
    threshold = flt(f.get("margin_threshold") or DEFAULT_MARGIN_THRESHOLD)
    rows = get_job_360_rows(filters=f, include_alerts=False, include_gl=True)
    out = []
    for r in rows:
        if flt(r.get("gl_revenue")) <= 0:
            continue
        if flt(r.get("gross_profit")) < 0 or flt(r.get("profit_margin_pct")) < threshold:
            out.append(r)
    return out


def get_jobs_negative_margin(filters=None):
    rows = get_job_360_rows(filters=filters, include_alerts=False, include_gl=True)
    return [r for r in rows if flt(r.get("gross_profit")) < 0]


def get_jobs_stale_wip(filters=None, stale_days=DEFAULT_STALE_DAYS):
    f = _to_dict(filters or {})
    f["stale_days"] = stale_days
    rows = get_recognition_aging(f)
    return [r for r in rows if r.get("wip_stale")]


def get_jobs_stale_accrual(filters=None, stale_days=DEFAULT_STALE_DAYS):
    f = _to_dict(filters or {})
    f["stale_days"] = stale_days
    rows = get_recognition_aging(f)
    return [r for r in rows if r.get("accrual_stale")]


def get_jobs_with_overdue_ar(filters=None, overdue_days=DEFAULT_AR_OVERDUE_DAYS):
    rows = get_jobs_ar(filters)
    out = defaultdict(lambda: {"job_number": None, "amount": 0.0, "max_age": 0, "invoice_count": 0})
    for r in rows:
        if cint(r.get("days_overdue")) <= overdue_days:
            continue
        jn = r.get("job_number")
        if not jn:
            continue
        bucket = out[jn]
        bucket["job_number"] = jn
        bucket["amount"] += flt(r.get("outstanding_amount"))
        bucket["invoice_count"] += 1
        bucket["max_age"] = max(bucket["max_age"], cint(r.get("days_overdue")))
    return list(out.values())


def get_closed_jobs_with_open_balances(filters=None):
    """Job Numbers in a Closed/Completed/Cancelled state that still have non-zero exposure."""
    rows = get_job_360_rows(filters=filters, include_alerts=False, include_gl=True)
    out = []
    for r in rows:
        status = (r.get("ops_status") or "").strip()
        if status not in CLOSED_STATUS_TOKENS:
            continue
        has_balance = (
            abs(flt(r.get("wip_amount"))) >= 0.01
            or abs(flt(r.get("accrual_amount"))) >= 0.01
            or flt(r.get("ar_outstanding")) > 0.01
            or flt(r.get("ap_outstanding")) > 0.01
        )
        if has_balance:
            out.append(r)
    return out


# ---------------------------------------------------------------------------
# Notification scheduled-method handlers
# ---------------------------------------------------------------------------

def _publish_notification(rows, title_key, message_template, route_template=None):
    """Send a Frappe notification log to job owners for each row."""
    from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

    if not rows:
        return 0
    sent = 0
    for r in rows:
        owner = r.get("owner")
        job_number = r.get("job_number")
        if not job_number:
            continue
        recipients = [owner] if owner else []
        if not recipients:
            continue
        try:
            enqueue_create_notification(
                recipients,
                {
                    "subject": title_key,
                    "type": "Alert",
                    "document_type": "Job Number",
                    "document_name": job_number,
                    "from_user": frappe.session.user,
                    "email_content": message_template.format(**r),
                },
            )
            sent += 1
        except Exception:
            frappe.log_error(frappe.get_traceback(), "job_360.notify:{0}".format(job_number))
    return sent


def notify_jobs_below_margin():
    rows = get_jobs_below_margin()
    return _publish_notification(
        rows,
        title_key=_("Job margin below threshold"),
        message_template=_(
            "Job {job_number} ({job_type} {job_no}) has GP {gross_profit} and margin {profit_margin_pct}%."
        ),
    )


def notify_jobs_negative_margin():
    rows = get_jobs_negative_margin()
    return _publish_notification(
        rows,
        title_key=_("Job has negative margin"),
        message_template=_(
            "Job {job_number} ({job_type} {job_no}) has negative GP {gross_profit}."
        ),
    )


def notify_stale_wip():
    rows = get_jobs_stale_wip()
    return _publish_notification(
        rows,
        title_key=_("Stale WIP balance"),
        message_template=_(
            "Job {job_number} carries open WIP {wip_balance} ({wip_age_days} days old)."
        ),
    )


def notify_stale_accrual():
    rows = get_jobs_stale_accrual()
    return _publish_notification(
        rows,
        title_key=_("Stale accrual balance"),
        message_template=_(
            "Job {job_number} carries open accrual {accrual_balance} ({accrual_age_days} days old)."
        ),
    )


def notify_overdue_ar():
    rows = get_jobs_with_overdue_ar()
    return _publish_notification(
        rows,
        title_key=_("Job has overdue receivables"),
        message_template=_(
            "Job {job_number} has overdue AR of {amount} ({invoice_count} invoices, oldest {max_age} days)."
        ),
    )


def notify_closed_jobs_with_balances():
    rows = get_closed_jobs_with_open_balances()
    return _publish_notification(
        rows,
        title_key=_("Closed job has open balances"),
        message_template=_(
            "Job {job_number} ({ops_status}) still has WIP {wip_amount} / Accrual {accrual_amount} / "
            "AR {ar_outstanding} / AP {ap_outstanding}."
        ),
    )


# ---------------------------------------------------------------------------
# Column factories for script reports
# ---------------------------------------------------------------------------

def col(field, label, ftype="Data", width=120, options=None):
    c = {"fieldname": field, "label": _(label), "fieldtype": ftype, "width": width}
    if options:
        c["options"] = options
    return c


def common_filters_meta():
    """Filter metadata used by every Job 360 script report."""
    return [
        {"fieldname": "company", "label": _("Company"), "fieldtype": "Link", "options": "Company"},
        {"fieldname": "branch", "label": _("Branch"), "fieldtype": "Link", "options": "Branch"},
        {"fieldname": "cost_center", "label": _("Cost Center"), "fieldtype": "Link", "options": "Cost Center"},
        {"fieldname": "profit_center", "label": _("Profit Center"), "fieldtype": "Link", "options": "Profit Center"},
        {"fieldname": "job_type", "label": _("Job Type"), "fieldtype": "Link", "options": "DocType"},
        {"fieldname": "from_date", "label": _("From Date"), "fieldtype": "Date"},
        {"fieldname": "to_date", "label": _("To Date"), "fieldtype": "Date"},
    ]


def chart_for(rows, label_field, value_field, dataset_label=None, chart_type="bar"):
    if not rows:
        return None
    labels = [str(r.get(label_field) or _("Unknown")) for r in rows]
    values = [flt(r.get(value_field)) for r in rows]
    return {
        "data": {
            "labels": labels,
            "datasets": [{"name": dataset_label or _("Value"), "values": values}],
        },
        "type": chart_type,
        "colors": ["#5e64ff", "#28a745", "#dc3545", "#ffa00a", "#6f42c1"],
    }

