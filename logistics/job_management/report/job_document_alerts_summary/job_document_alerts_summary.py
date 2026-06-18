# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from frappe import _
from frappe.utils import cint

from logistics.job_management.job_360 import chart_for, col, get_job_360_rows


def execute(filters=None):
    rows = get_job_360_rows(filters=filters, include_alerts=True, include_gl=False)
    rows = [r for r in rows if (cint(r.get("alerts_overdue")) + cint(r.get("alerts_missing")) + cint(r.get("alerts_expiring"))) > 0]
    rows.sort(key=lambda r: -(cint(r.get("alerts_overdue")) * 10 + cint(r.get("alerts_missing")) + cint(r.get("alerts_expiring"))))
    columns = _columns()
    chart = chart_for(
        rows[:15],
        label_field="job_number",
        value_field="alerts_overdue",
        dataset_label=_("Overdue Documents"),
    )
    return columns, rows, None, chart, _summary(rows)


def _columns():
    return [
        col("job_number", "Job Number", "Link", 160, options="Job Number"),
        col("job_type", "Type", "Data", 110),
        col("customer", "Customer", "Link", 140, options="Customer"),
        col("ops_status", "Status", "Data", 110),
        col("alerts_overdue", "Overdue", "Int", 90),
        col("alerts_missing", "Missing", "Int", 90),
        col("alerts_expiring", "Expiring Soon", "Int", 110),
        col("alerts_total", "Total Tracked", "Int", 110),
    ]


def _summary(rows):
    overdue = sum(cint(r.get("alerts_overdue")) for r in rows)
    missing = sum(cint(r.get("alerts_missing")) for r in rows)
    expiring = sum(cint(r.get("alerts_expiring")) for r in rows)
    return [
        {"label": _("Jobs With Alerts"), "value": len(rows), "indicator": "yellow"},
        {"label": _("Overdue Docs"), "value": overdue, "indicator": "red" if overdue else "green"},
        {"label": _("Missing Docs"), "value": missing, "indicator": "yellow" if missing else "green"},
        {"label": _("Expiring Soon"), "value": expiring, "indicator": "orange" if expiring else "green"},
    ]
