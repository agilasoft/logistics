# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from frappe import _
from frappe.utils import flt

from logistics.job_management.job_360 import (
    DEFAULT_MARGIN_THRESHOLD,
    chart_for,
    col,
    get_job_360_rows,
)


def execute(filters=None):
    threshold = flt((filters or {}).get("margin_threshold") or DEFAULT_MARGIN_THRESHOLD)
    rows = get_job_360_rows(filters=filters, include_alerts=False, include_gl=True)
    flagged = []
    for r in rows:
        if flt(r.get("gl_revenue")) <= 0:
            continue
        if flt(r.get("gross_profit")) < 0 or flt(r.get("profit_margin_pct")) < threshold:
            flagged.append(r)
    flagged.sort(key=lambda r: flt(r.get("profit_margin_pct")))
    columns = _columns()
    chart = chart_for(
        flagged[:15],
        label_field="job_number",
        value_field="profit_margin_pct",
        dataset_label=_("Margin %"),
    )
    return columns, flagged, None, chart, _summary(flagged, threshold)


def _columns():
    return [
        col("job_number", "Job Number", "Link", 160, options="Job Number"),
        col("job_type", "Type", "Data", 110),
        col("customer", "Customer", "Link", 140, options="Customer"),
        col("company", "Company", "Link", 110, options="Company"),
        col("gl_revenue", "Revenue", "Currency", 110),
        col("gl_cost", "Cost", "Currency", 110),
        col("gross_profit", "GP", "Currency", 110),
        col("profit_margin_pct", "Margin %", "Float", 100),
        col("ar_outstanding", "AR Outstanding", "Currency", 130),
        col("ap_outstanding", "AP Outstanding", "Currency", 130),
        col("ops_status", "Status", "Data", 110),
    ]


def _summary(rows, threshold):
    if not rows:
        return [{"label": _("Watchlist"), "value": 0, "indicator": "green"}]
    negative = sum(1 for r in rows if flt(r.get("gross_profit")) < 0)
    return [
        {"label": _("Total Flagged"), "value": len(rows), "indicator": "yellow"},
        {"label": _("Negative GP"), "value": negative, "indicator": "red"},
        {"label": _("Threshold %"), "value": flt(threshold, 2), "datatype": "Float"},
    ]
