# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from frappe import _
from frappe.utils import cint, flt

from logistics.job_management.job_360 import chart_for, col, get_recognition_aging


def execute(filters=None):
    rows = get_recognition_aging(filters)
    columns = _columns()
    chart = chart_for(
        sorted(rows, key=lambda r: -cint(r.get("wip_age_days")))[:15],
        label_field="job_number",
        value_field="wip_age_days",
        dataset_label=_("WIP Age (days)"),
    )
    return columns, rows, None, chart, _summary(rows)


def _columns():
    return [
        col("job_number", "Job Number", "Link", 160, options="Job Number"),
        col("job_type", "Type", "Data", 110),
        col("company", "Company", "Link", 110, options="Company"),
        col("branch", "Branch", "Link", 100, options="Branch"),
        col("wip_account", "WIP Account", "Link", 140, options="Account"),
        col("wip_balance", "WIP Balance", "Currency", 110),
        col("wip_age_days", "WIP Age (days)", "Int", 110),
        col("wip_oldest_date", "WIP Oldest", "Date", 110),
        col("wip_aging_bucket", "WIP Bucket", "Data", 90),
        col("wip_stale", "WIP Stale", "Check", 80),
        col("accrual_account", "Accrual Account", "Link", 140, options="Account"),
        col("accrual_balance", "Accrual Balance", "Currency", 120),
        col("accrual_age_days", "Accrual Age", "Int", 110),
        col("accrual_oldest_date", "Accrual Oldest", "Date", 110),
        col("accrual_aging_bucket", "Accrual Bucket", "Data", 100),
        col("accrual_stale", "Accrual Stale", "Check", 100),
    ]


def _summary(rows):
    if not rows:
        return [{"label": _("Aged Jobs"), "value": 0, "indicator": "green"}]
    stale_wip = sum(1 for r in rows if r.get("wip_stale"))
    stale_accr = sum(1 for r in rows if r.get("accrual_stale"))
    total_wip = sum(flt(r.get("wip_balance")) for r in rows)
    total_accr = sum(flt(r.get("accrual_balance")) for r in rows)
    return [
        {"label": _("Aged Jobs"), "value": len(rows), "indicator": "yellow"},
        {"label": _("Stale WIP"), "value": stale_wip, "indicator": "red" if stale_wip else "green"},
        {"label": _("Stale Accrual"), "value": stale_accr, "indicator": "red" if stale_accr else "green"},
        {"label": _("Total WIP"), "value": flt(total_wip, 2), "datatype": "Currency"},
        {"label": _("Total Accrual"), "value": flt(total_accr, 2), "datatype": "Currency"},
    ]
