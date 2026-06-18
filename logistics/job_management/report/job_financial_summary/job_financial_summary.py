# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from frappe import _
from frappe.utils import flt

from logistics.job_management.job_360 import chart_for, col, get_job_360_rows


def execute(filters=None):
    rows = get_job_360_rows(filters=filters, include_alerts=False, include_gl=True)
    columns = _columns()
    chart = chart_for(
        sorted(rows, key=lambda r: -flt(r.get("gl_revenue")))[:15],
        label_field="job_number",
        value_field="gl_revenue",
        dataset_label=_("Revenue"),
    )
    summary = _summary(rows)
    return columns, rows, None, chart, summary


def _columns():
    return [
        col("job_number", "Job Number", "Link", 150, options="Job Number"),
        col("job_type", "Type", "Data", 110),
        col("company", "Company", "Link", 110, options="Company"),
        col("branch", "Branch", "Link", 100, options="Branch"),
        col("profit_center", "Profit Center", "Link", 110, options="Profit Center"),
        col("estimated_revenue", "Est Rev", "Currency", 110),
        col("estimated_costs", "Est Cost", "Currency", 110),
        col("gl_revenue", "GL Rev", "Currency", 110),
        col("gl_cost", "GL Cost", "Currency", 110),
        col("gross_profit", "GP", "Currency", 110),
        col("profit_margin_pct", "Margin %", "Float", 90),
        col("wip_amount", "WIP (GL)", "Currency", 110),
        col("accrual_amount", "Accrual (GL)", "Currency", 110),
        col("disbursements_amount", "Disbursements", "Currency", 120),
        col("recognized_revenue", "Recognized Rev", "Currency", 130),
        col("recognized_costs", "Recognized Cost", "Currency", 130),
    ]


def _summary(rows):
    if not rows:
        return []
    total_rev = sum(flt(r.get("gl_revenue")) for r in rows)
    total_cost = sum(flt(r.get("gl_cost")) for r in rows)
    total_gp = sum(flt(r.get("gross_profit")) for r in rows)
    margin = (total_gp / total_rev * 100.0) if total_rev else 0.0
    return [
        {"label": _("Jobs"), "value": len(rows), "indicator": "blue"},
        {"label": _("Revenue"), "value": flt(total_rev, 2), "datatype": "Currency", "indicator": "green"},
        {"label": _("Cost"), "value": flt(total_cost, 2), "datatype": "Currency", "indicator": "red"},
        {"label": _("GP"), "value": flt(total_gp, 2), "datatype": "Currency"},
        {"label": _("Margin %"), "value": flt(margin, 2), "datatype": "Float"},
    ]
