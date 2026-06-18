# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from collections import defaultdict

from frappe import _
from frappe.utils import flt

from logistics.job_management.job_360 import chart_for, col, get_jobs_ap


def execute(filters=None):
    rows = get_jobs_ap(filters)
    summary_rows = _per_job_summary(rows)
    columns = _columns()
    chart = chart_for(
        [
            {"bucket": "0-30", "amount": sum(flt(r.get("0-30")) for r in summary_rows)},
            {"bucket": "31-60", "amount": sum(flt(r.get("31-60")) for r in summary_rows)},
            {"bucket": "61-90", "amount": sum(flt(r.get("61-90")) for r in summary_rows)},
            {"bucket": "91+", "amount": sum(flt(r.get("91+")) for r in summary_rows)},
        ],
        label_field="bucket",
        value_field="amount",
        dataset_label=_("Outstanding"),
    )
    return columns, summary_rows, None, chart, _summary(summary_rows)


def _per_job_summary(rows):
    grouped = defaultdict(lambda: {
        "0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "91+": 0.0,
        "total": 0.0, "invoice_count": 0, "company": None,
    })
    for r in rows:
        jn = r.get("job_number")
        if not jn:
            continue
        bucket = grouped[jn]
        bucket["job_number"] = jn
        bucket["company"] = r.get("company")
        bucket[r["age_bucket"]] += flt(r.get("outstanding_amount"))
        bucket["total"] += flt(r.get("outstanding_amount"))
        bucket["invoice_count"] += 1
    out = list(grouped.values())
    out.sort(key=lambda r: -flt(r.get("total")))
    return out


def _columns():
    return [
        col("job_number", "Job Number", "Link", 160, options="Job Number"),
        col("company", "Company", "Link", 110, options="Company"),
        col("invoice_count", "Invoices", "Int", 80),
        col("0-30", "0-30 Days", "Currency", 110),
        col("31-60", "31-60 Days", "Currency", 110),
        col("61-90", "61-90 Days", "Currency", 110),
        col("91+", "91+ Days", "Currency", 110),
        col("total", "Total Outstanding", "Currency", 140),
    ]


def _summary(rows):
    total = sum(flt(r.get("total")) for r in rows)
    over_90 = sum(flt(r.get("91+")) for r in rows)
    return [
        {"label": _("Jobs with AP"), "value": len(rows), "indicator": "blue"},
        {"label": _("Total Outstanding"), "value": flt(total, 2), "datatype": "Currency", "indicator": "yellow"},
        {"label": _("Over 90 Days"), "value": flt(over_90, 2), "datatype": "Currency", "indicator": "red"},
    ]
