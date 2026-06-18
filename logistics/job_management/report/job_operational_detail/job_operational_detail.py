# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from frappe import _

from logistics.job_management.job_360 import chart_for, col, get_job_360_rows


def execute(filters=None):
    rows = get_job_360_rows(filters=filters, include_alerts=True, include_gl=False)
    columns = _columns()
    by_type = {}
    for r in rows:
        by_type[r.get("job_type") or _("Unknown")] = by_type.get(r.get("job_type") or _("Unknown"), 0) + 1
    chart_rows = [{"job_type": k, "count": v} for k, v in by_type.items()]
    chart = chart_for(chart_rows, label_field="job_type", value_field="count", dataset_label=_("Jobs"))
    return columns, rows, None, chart, []


def _columns():
    return [
        col("job_number", "Job Number", "Link", 160, options="Job Number"),
        col("job_type", "Type", "Data", 110),
        col("job_no", "Source Job", "Dynamic Link", 160, options="job_type"),
        col("customer", "Customer", "Link", 140, options="Customer"),
        col("origin", "Origin", "Data", 100),
        col("destination", "Destination", "Data", 100),
        col("mode", "Mode", "Data", 100),
        col("vehicle_or_carrier", "Carrier/Vehicle", "Data", 130),
        col("etd", "ETD", "Date", 90),
        col("eta", "ETA", "Date", 90),
        col("ops_status", "Ops Status", "Data", 110),
        col("billing_status", "Billing Status", "Data", 110),
        col("sla_status", "SLA Status", "Data", 100),
        col("branch", "Branch", "Link", 100, options="Branch"),
        col("profit_center", "Profit Center", "Link", 110, options="Profit Center"),
        col("alerts_overdue", "Overdue Docs", "Int", 100),
    ]
