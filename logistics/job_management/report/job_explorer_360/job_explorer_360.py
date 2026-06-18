# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""``Job Explorer 360`` script report.

Cross-module per-Job Number drill-down used to be a custom Page at
``/app/job-360-explorer``. The page is retired; this Script Report is its
replacement and benefits from the standard Report Builder UI (filters,
export, saved views) while keeping the same underlying data layer:

* Same ``logistics.job_management.job_360`` helpers (no duplicated SQL).
* Chart (Top 15 jobs by Gross Profit) shown above the table.
* Report Summary tiles (Revenue, Cost, GP, Margin %, WIP, Accrual, AR, AP).

Workspace number cards (Open Jobs, Negative Margin Jobs, ...) sit alongside
this report on the Job Management workspace.
"""

from __future__ import unicode_literals

from frappe import _
from frappe.utils import flt

from logistics.job_management.job_360 import (
	chart_for,
	col,
	get_job_360_rows,
)


def execute(filters=None):
	rows = get_job_360_rows(filters=filters, include_alerts=True, include_gl=True)
	columns = _columns()
	chart = chart_for(
		sorted(rows, key=lambda r: -flt(r.get("gross_profit")))[:15],
		label_field="job_number",
		value_field="gross_profit",
		dataset_label=_("Gross Profit"),
	)
	summary = _summary(rows)
	return columns, rows, None, chart, summary


def _columns():
	return [
		col("job_number", "Job Number", "Link", 150, options="Job Number"),
		col("job_type", "Type", "Data", 110),
		col("job_no", "Source Job", "Dynamic Link", 160, options="job_type"),
		col("company", "Company", "Link", 110, options="Company"),
		col("branch", "Branch", "Link", 100, options="Branch"),
		col("profit_center", "Profit Center", "Link", 110, options="Profit Center"),
		col("customer", "Customer", "Link", 140, options="Customer"),
		col("origin", "Origin", "Data", 100),
		col("destination", "Destination", "Data", 100),
		col("ops_status", "Ops Status", "Data", 110),
		col("etd", "ETD", "Date", 90),
		col("eta", "ETA", "Date", 90),
		col("estimated_revenue", "Est Rev", "Currency", 110),
		col("estimated_costs", "Est Cost", "Currency", 110),
		col("gl_revenue", "GL Rev", "Currency", 110),
		col("gl_cost", "GL Cost", "Currency", 110),
		col("gross_profit", "GP", "Currency", 110),
		col("profit_margin_pct", "Margin %", "Float", 90),
		col("wip_amount", "WIP", "Currency", 100),
		col("accrual_amount", "Accrual", "Currency", 100),
		col("disbursements_amount", "Disb.", "Currency", 100),
		col("ar_outstanding", "AR Outstanding", "Currency", 120),
		col("ap_outstanding", "AP Outstanding", "Currency", 120),
		col("alerts_overdue", "Overdue Docs", "Int", 100),
		col("alerts_missing", "Missing Docs", "Int", 100),
		col("recognition_date", "Recognition Date", "Date", 110),
	]


def _summary(rows):
	if not rows:
		return []
	total_rev = sum(flt(r.get("gl_revenue")) for r in rows)
	total_cost = sum(flt(r.get("gl_cost")) for r in rows)
	total_gp = sum(flt(r.get("gross_profit")) for r in rows)
	total_wip = sum(flt(r.get("wip_amount")) for r in rows)
	total_accr = sum(flt(r.get("accrual_amount")) for r in rows)
	total_ar = sum(flt(r.get("ar_outstanding")) for r in rows)
	total_ap = sum(flt(r.get("ap_outstanding")) for r in rows)
	margin = (total_gp / total_rev * 100.0) if total_rev else 0.0
	return [
		{"label": _("Jobs"), "value": len(rows), "indicator": "blue"},
		{"label": _("Revenue"), "value": flt(total_rev, 2), "datatype": "Currency", "indicator": "green"},
		{"label": _("Cost"), "value": flt(total_cost, 2), "datatype": "Currency", "indicator": "red"},
		{"label": _("GP"), "value": flt(total_gp, 2), "datatype": "Currency", "indicator": "green" if total_gp >= 0 else "red"},
		{"label": _("Margin %"), "value": flt(margin, 2), "datatype": "Float", "indicator": "blue"},
		{"label": _("WIP"), "value": flt(total_wip, 2), "datatype": "Currency", "indicator": "orange"},
		{"label": _("Accrual"), "value": flt(total_accr, 2), "datatype": "Currency", "indicator": "orange"},
		{"label": _("AR"), "value": flt(total_ar, 2), "datatype": "Currency", "indicator": "yellow"},
		{"label": _("AP"), "value": flt(total_ap, 2), "datatype": "Currency", "indicator": "yellow"},
	]
