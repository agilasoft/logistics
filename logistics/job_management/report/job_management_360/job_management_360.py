# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""``Job Management 360`` script report.

Executive monthly view of every Job Number plus its joined financials.
Replaces the standalone ``Job Management 360`` Dashboard with a Frappe
Report Builder surface that bundles:

* One row per registration month (``Job Number.creation``) — jobs opened,
  Revenue / Cost / GP / Margin %, plus WIP, Accrual, AR and AP balances
  attributable to those jobs.
* A multi-series line chart (Revenue vs Cost vs Gross Profit per month).
* Report Summary tiles for the period totals (Jobs, Revenue, Cost, GP,
  Margin %, WIP, Accrual, AR, AP).

The 10 standing Dashboard Number Cards (Open Jobs, Negative Margin Jobs,
Outstanding Receivables, ...) are kept and shown directly on the Job
Management workspace next to this report shortcut.
"""

from __future__ import unicode_literals

from collections import defaultdict

from frappe import _
from frappe.utils import flt

from logistics.job_management.job_360 import (
	col,
	get_job_360_rows,
)


def execute(filters=None):
	rows = get_job_360_rows(filters=filters, include_alerts=False, include_gl=True)
	monthly = _aggregate_by_month(rows)
	columns = _columns()
	chart = _monthly_chart(monthly)
	summary = _summary(rows, monthly)
	return columns, monthly, None, chart, summary


def _columns():
	return [
		col("month", "Month", "Data", 100),
		col("jobs_opened", "Jobs Opened", "Int", 110),
		col("revenue", "Revenue", "Currency", 130),
		col("cost", "Cost", "Currency", 130),
		col("gross_profit", "Gross Profit", "Currency", 140),
		col("margin_pct", "Margin %", "Float", 100),
		col("wip_amount", "WIP", "Currency", 120),
		col("accrual_amount", "Accrual", "Currency", 120),
		col("ar_outstanding", "AR Outstanding", "Currency", 140),
		col("ap_outstanding", "AP Outstanding", "Currency", 140),
	]


def _aggregate_by_month(rows):
	buckets = defaultdict(lambda: {
		"jobs": 0,
		"revenue": 0.0,
		"cost": 0.0,
		"gp": 0.0,
		"wip": 0.0,
		"accrual": 0.0,
		"ar": 0.0,
		"ap": 0.0,
	})
	for r in rows:
		month = _month_key(r.get("creation"))
		if not month:
			continue
		b = buckets[month]
		b["jobs"] += 1
		b["revenue"] += flt(r.get("gl_revenue") or r.get("revenue"))
		b["cost"] += flt(r.get("gl_cost") or r.get("cost"))
		b["gp"] += flt(r.get("gross_profit"))
		b["wip"] += flt(r.get("wip_amount"))
		b["accrual"] += flt(r.get("accrual_amount"))
		b["ar"] += flt(r.get("ar_outstanding"))
		b["ap"] += flt(r.get("ap_outstanding"))

	out = []
	for month in sorted(buckets):
		b = buckets[month]
		margin = (b["gp"] / b["revenue"] * 100.0) if b["revenue"] else 0.0
		out.append({
			"month": month,
			"jobs_opened": b["jobs"],
			"revenue": flt(b["revenue"], 2),
			"cost": flt(b["cost"], 2),
			"gross_profit": flt(b["gp"], 2),
			"margin_pct": flt(margin, 2),
			"wip_amount": flt(b["wip"], 2),
			"accrual_amount": flt(b["accrual"], 2),
			"ar_outstanding": flt(b["ar"], 2),
			"ap_outstanding": flt(b["ap"], 2),
		})
	return out


def _month_key(value):
	"""Normalise ``Job Number.creation`` (datetime or str) to ``YYYY-MM``."""
	if not value:
		return None
	if hasattr(value, "strftime"):
		return value.strftime("%Y-%m")
	s = str(value)
	return s[:7] if len(s) >= 7 else None


def _monthly_chart(monthly):
	if not monthly:
		return None
	labels = [r["month"] for r in monthly]
	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Revenue"), "values": [r["revenue"] for r in monthly]},
				{"name": _("Cost"), "values": [r["cost"] for r in monthly]},
				{"name": _("Gross Profit"), "values": [r["gross_profit"] for r in monthly]},
			],
		},
		"type": "line",
		"colors": ["#28a745", "#dc3545", "#5e64ff"],
		"lineOptions": {"regionFill": 0, "hideDots": 0},
		"axisOptions": {"xIsSeries": 1},
	}


def _summary(rows, monthly):
	if not rows:
		return []
	total_jobs = sum(b["jobs_opened"] for b in monthly) or len(rows)
	total_rev = sum(b["revenue"] for b in monthly)
	total_cost = sum(b["cost"] for b in monthly)
	total_gp = sum(b["gross_profit"] for b in monthly)
	total_wip = sum(b["wip_amount"] for b in monthly)
	total_accr = sum(b["accrual_amount"] for b in monthly)
	total_ar = sum(b["ar_outstanding"] for b in monthly)
	total_ap = sum(b["ap_outstanding"] for b in monthly)
	margin = (total_gp / total_rev * 100.0) if total_rev else 0.0
	return [
		{"label": _("Jobs Opened"), "value": total_jobs, "indicator": "blue"},
		{"label": _("Revenue"), "value": flt(total_rev, 2), "datatype": "Currency", "indicator": "green"},
		{"label": _("Cost"), "value": flt(total_cost, 2), "datatype": "Currency", "indicator": "red"},
		{"label": _("Gross Profit"), "value": flt(total_gp, 2), "datatype": "Currency", "indicator": "green" if total_gp >= 0 else "red"},
		{"label": _("Margin %"), "value": flt(margin, 2), "datatype": "Float", "indicator": "blue"},
		{"label": _("WIP"), "value": flt(total_wip, 2), "datatype": "Currency", "indicator": "orange"},
		{"label": _("Accrual"), "value": flt(total_accr, 2), "datatype": "Currency", "indicator": "orange"},
		{"label": _("AR Outstanding"), "value": flt(total_ar, 2), "datatype": "Currency", "indicator": "yellow"},
		{"label": _("AP Outstanding"), "value": flt(total_ap, 2), "datatype": "Currency", "indicator": "yellow"},
	]
