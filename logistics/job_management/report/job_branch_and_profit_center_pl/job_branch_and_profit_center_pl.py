# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from collections import defaultdict

from frappe import _
from frappe.utils import flt

from logistics.job_management.job_360 import chart_for, col, get_job_360_rows


def execute(filters=None):
    rows = get_job_360_rows(filters=filters, include_alerts=False, include_gl=True)
    grouped = defaultdict(lambda: {"branch": None, "profit_center": None, "jobs": 0,
                                   "revenue": 0.0, "cost": 0.0, "gp": 0.0,
                                   "wip": 0.0, "accrual": 0.0, "ar": 0.0, "ap": 0.0})
    for r in rows:
        key = ((r.get("branch") or _("(no branch)")), (r.get("profit_center") or _("(no PC)")))
        bucket = grouped[key]
        bucket["branch"] = key[0]
        bucket["profit_center"] = key[1]
        bucket["jobs"] += 1
        bucket["revenue"] += flt(r.get("gl_revenue"))
        bucket["cost"] += flt(r.get("gl_cost"))
        bucket["gp"] += flt(r.get("gross_profit"))
        bucket["wip"] += flt(r.get("wip_amount"))
        bucket["accrual"] += flt(r.get("accrual_amount"))
        bucket["ar"] += flt(r.get("ar_outstanding"))
        bucket["ap"] += flt(r.get("ap_outstanding"))

    out = []
    for v in grouped.values():
        v["margin_pct"] = flt((v["gp"] / v["revenue"] * 100.0) if v["revenue"] else 0, 2)
        out.append(v)
    out.sort(key=lambda r: -flt(r.get("gp")))
    columns = _columns()
    chart = chart_for(out[:15], label_field="branch", value_field="gp", dataset_label=_("Gross Profit"))
    return columns, out, None, chart, _summary(out)


def _columns():
    return [
        col("branch", "Branch", "Data", 130),
        col("profit_center", "Profit Center", "Data", 140),
        col("jobs", "Jobs", "Int", 80),
        col("revenue", "Revenue", "Currency", 120),
        col("cost", "Cost", "Currency", 120),
        col("gp", "GP", "Currency", 120),
        col("margin_pct", "Margin %", "Float", 100),
        col("wip", "WIP", "Currency", 110),
        col("accrual", "Accrual", "Currency", 110),
        col("ar", "AR Outstanding", "Currency", 130),
        col("ap", "AP Outstanding", "Currency", 130),
    ]


def _summary(rows):
    if not rows:
        return []
    return [
        {"label": _("Branches/PCs"), "value": len(rows), "indicator": "blue"},
        {"label": _("Revenue"), "value": flt(sum(flt(r["revenue"]) for r in rows), 2), "datatype": "Currency"},
        {"label": _("GP"), "value": flt(sum(flt(r["gp"]) for r in rows), 2), "datatype": "Currency"},
    ]
