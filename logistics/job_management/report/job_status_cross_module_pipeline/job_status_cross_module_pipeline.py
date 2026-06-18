# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from frappe import _
from frappe.utils import cint, flt

from logistics.job_management.job_360 import chart_for, col, get_job_status_pipeline


def execute(filters=None):
    rows = get_job_status_pipeline(filters)
    columns = _columns()
    chart = chart_for(
        sorted(rows, key=lambda r: -cint(r.get("count")))[:15],
        label_field="status",
        value_field="count",
        dataset_label=_("Jobs"),
    )
    return columns, rows, None, chart, _summary(rows)


def _columns():
    return [
        col("job_type", "Job Type", "Data", 130),
        col("status", "Status", "Data", 130),
        col("count", "Jobs", "Int", 90),
        col("value", "Estimated Revenue", "Currency", 140),
    ]


def _summary(rows):
    total_jobs = sum(cint(r.get("count")) for r in rows)
    total_value = sum(flt(r.get("value")) for r in rows)
    return [
        {"label": _("Total Jobs"), "value": total_jobs, "indicator": "blue"},
        {"label": _("Estimated Revenue"), "value": flt(total_value, 2), "datatype": "Currency", "indicator": "green"},
    ]
