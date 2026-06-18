# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from collections import OrderedDict, defaultdict

from frappe import _
from frappe.utils import flt, getdate

from logistics.job_management.job_360 import col, get_job_360_rows


def execute(filters=None):
    rows = get_job_360_rows(filters=filters, include_alerts=False, include_gl=True)
    monthly = defaultdict(lambda: {"period": None, "revenue": 0.0, "cost": 0.0, "gp": 0.0, "jobs": 0})
    for r in rows:
        d = r.get("recognition_date") or r.get("job_open_date") or r.get("creation")
        if not d:
            continue
        period = getdate(d).strftime("%Y-%m")
        bucket = monthly[period]
        bucket["period"] = period
        bucket["revenue"] += flt(r.get("gl_revenue"))
        bucket["cost"] += flt(r.get("gl_cost"))
        bucket["gp"] += flt(r.get("gross_profit"))
        bucket["jobs"] += 1

    sorted_rows = sorted(monthly.values(), key=lambda r: r["period"] or "")
    for row in sorted_rows:
        row["margin_pct"] = flt((row["gp"] / row["revenue"] * 100.0) if row["revenue"] else 0, 2)
    columns = _columns()
    chart = _grouped_chart(sorted_rows)
    return columns, sorted_rows, None, chart, _summary(sorted_rows)


def _columns():
    return [
        col("period", "Period", "Data", 100),
        col("jobs", "Jobs", "Int", 80),
        col("revenue", "Revenue", "Currency", 120),
        col("cost", "Cost", "Currency", 120),
        col("gp", "GP", "Currency", 120),
        col("margin_pct", "Margin %", "Float", 100),
    ]


def _grouped_chart(rows):
    if not rows:
        return None
    labels = [r["period"] for r in rows]
    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": _("Revenue"), "values": [flt(r["revenue"]) for r in rows]},
                {"name": _("Cost"), "values": [flt(r["cost"]) for r in rows]},
                {"name": _("GP"), "values": [flt(r["gp"]) for r in rows]},
            ],
        },
        "type": "bar",
        "colors": ["#28a745", "#dc3545", "#5e64ff"],
    }


def _summary(rows):
    if not rows:
        return []
    rev = sum(flt(r["revenue"]) for r in rows)
    cost = sum(flt(r["cost"]) for r in rows)
    gp = sum(flt(r["gp"]) for r in rows)
    return [
        {"label": _("Months"), "value": len(rows), "indicator": "blue"},
        {"label": _("Revenue"), "value": flt(rev, 2), "datatype": "Currency"},
        {"label": _("Cost"), "value": flt(cost, 2), "datatype": "Currency"},
        {"label": _("GP"), "value": flt(gp, 2), "datatype": "Currency"},
    ]
