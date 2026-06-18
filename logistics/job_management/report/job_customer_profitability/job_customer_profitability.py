# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from collections import defaultdict

from frappe import _
from frappe.utils import flt

from logistics.job_management.job_360 import chart_for, col, get_job_360_rows


def execute(filters=None):
    rows = get_job_360_rows(filters=filters, include_alerts=False, include_gl=True)
    grouped = defaultdict(lambda: {"customer": None, "jobs": 0,
                                   "revenue": 0.0, "cost": 0.0, "gp": 0.0,
                                   "ar": 0.0, "wip": 0.0})
    for r in rows:
        key = r.get("customer") or _("(no customer)")
        bucket = grouped[key]
        bucket["customer"] = key
        bucket["jobs"] += 1
        bucket["revenue"] += flt(r.get("gl_revenue"))
        bucket["cost"] += flt(r.get("gl_cost"))
        bucket["gp"] += flt(r.get("gross_profit"))
        bucket["ar"] += flt(r.get("ar_outstanding"))
        bucket["wip"] += flt(r.get("wip_amount"))

    out = []
    for v in grouped.values():
        v["margin_pct"] = flt((v["gp"] / v["revenue"] * 100.0) if v["revenue"] else 0, 2)
        out.append(v)
    out.sort(key=lambda r: -flt(r["gp"]))
    columns = _columns()
    chart = chart_for(out[:15], label_field="customer", value_field="gp", dataset_label=_("Gross Profit"))
    return columns, out, None, chart, _summary(out)


def _columns():
    return [
        col("customer", "Customer", "Link", 180, options="Customer"),
        col("jobs", "Jobs", "Int", 80),
        col("revenue", "Revenue", "Currency", 130),
        col("cost", "Cost", "Currency", 130),
        col("gp", "GP", "Currency", 130),
        col("margin_pct", "Margin %", "Float", 100),
        col("wip", "WIP", "Currency", 110),
        col("ar", "AR Outstanding", "Currency", 130),
    ]


def _summary(rows):
    if not rows:
        return []
    return [
        {"label": _("Customers"), "value": len(rows), "indicator": "blue"},
        {"label": _("Revenue"), "value": flt(sum(flt(r["revenue"]) for r in rows), 2), "datatype": "Currency"},
        {"label": _("GP"), "value": flt(sum(flt(r["gp"]) for r in rows), 2), "datatype": "Currency"},
    ]
