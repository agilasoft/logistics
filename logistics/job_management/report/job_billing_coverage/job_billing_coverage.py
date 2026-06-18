# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from frappe import _
from frappe.utils import flt

from logistics.job_management.job_360 import chart_for, col, get_job_360_rows


def execute(filters=None):
    rows = get_job_360_rows(filters=filters, include_alerts=False, include_gl=True)
    enriched = []
    for r in rows:
        est_rev = flt(r.get("estimated_revenue"))
        gl_rev = flt(r.get("gl_revenue"))
        ar = flt(r.get("ar_outstanding"))
        billed = gl_rev + ar
        enriched.append({
            **r,
            "billed": flt(billed, 2),
            "billing_gap_estimate": flt(est_rev - gl_rev, 2),
            "billing_gap_to_estimate": flt(est_rev - billed, 2),
            "coverage_pct": flt((gl_rev / est_rev * 100.0) if est_rev else 0, 2),
        })
    enriched.sort(key=lambda r: r["billing_gap_estimate"], reverse=True)
    columns = _columns()
    chart = chart_for(
        enriched[:15],
        label_field="job_number",
        value_field="billing_gap_estimate",
        dataset_label=_("Estimate − GL Rev"),
    )
    return columns, enriched, None, chart, _summary(enriched)


def _columns():
    return [
        col("job_number", "Job Number", "Link", 160, options="Job Number"),
        col("job_type", "Type", "Data", 110),
        col("customer", "Customer", "Link", 140, options="Customer"),
        col("estimated_revenue", "Estimated Rev", "Currency", 130),
        col("gl_revenue", "GL Revenue", "Currency", 120),
        col("ar_outstanding", "AR Outstanding", "Currency", 130),
        col("billed", "Billed (GL+AR)", "Currency", 130),
        col("billing_gap_estimate", "Gap (Est − GL)", "Currency", 140),
        col("billing_gap_to_estimate", "Gap (Est − Billed)", "Currency", 150),
        col("coverage_pct", "Coverage %", "Float", 100),
        col("ops_status", "Status", "Data", 110),
    ]


def _summary(rows):
    if not rows:
        return []
    est_total = sum(flt(r.get("estimated_revenue")) for r in rows)
    gl_total = sum(flt(r.get("gl_revenue")) for r in rows)
    return [
        {"label": _("Jobs"), "value": len(rows), "indicator": "blue"},
        {"label": _("Estimate"), "value": flt(est_total, 2), "datatype": "Currency"},
        {"label": _("GL Revenue"), "value": flt(gl_total, 2), "datatype": "Currency"},
        {"label": _("Gap"), "value": flt(est_total - gl_total, 2), "datatype": "Currency", "indicator": "yellow"},
    ]
