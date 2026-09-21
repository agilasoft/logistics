# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from collections import Counter

from frappe import _

from logistics.analytics_reports.bootstrap import series_chart
from logistics.high_value.hv_analytics import (
	apply_job_filters,
	apply_quote_filters,
	brand_board_rows,
	load_report_context,
)


def execute(filters=None):
	filters = filters or {}
	columns = _columns()
	brands, quotes, jobs = load_report_context(filters)
	brand = (filters.get("hv_brand") or filters.get("brand") or "").strip()
	if brand:
		brands = [b for b in brands if (b.get("name") if isinstance(b, dict) else b.name) == brand]
	quotes = apply_quote_filters(quotes, filters)
	jobs = apply_job_filters(jobs, filters)
	rows = brand_board_rows(brands, quotes, jobs)
	chart = _chart(rows)
	return columns, rows, None, chart, _summary(rows)


def _columns():
	return [
		{"label": _("Brand"), "fieldname": "name", "fieldtype": "Link", "options": "HV Brands", "width": 120},
		{"label": _("Brand Name"), "fieldname": "brand_name", "fieldtype": "Data", "width": 160},
		{"label": _("Severity"), "fieldname": "severity", "fieldtype": "Data", "width": 90},
		{"label": _("Quotes"), "fieldname": "quote_count", "fieldtype": "Int", "width": 80},
		{"label": _("Jobs"), "fieldname": "job_count", "fieldtype": "Int", "width": 80},
		{"label": _("Live"), "fieldname": "live_job_count", "fieldtype": "Int", "width": 70},
		{"label": _("SLA At Risk"), "fieldname": "sla_at_risk", "fieldtype": "Int", "width": 100},
		{"label": _("SLA Breached"), "fieldname": "sla_breached", "fieldtype": "Int", "width": 110},
		{"label": _("Est. Revenue"), "fieldname": "estimated_revenue", "fieldtype": "Currency", "width": 120},
		{"label": _("Est. Profit"), "fieldname": "estimated_profit", "fieldtype": "Currency", "width": 120},
		{"label": _("Owners"), "fieldname": "owners", "fieldtype": "Data", "width": 180},
	]


def _chart(rows):
	c = Counter((r.get("severity") or "idle") for r in rows)
	order = ["overdue", "at_risk", "live", "active", "idle"]
	data = [{"severity": k, "brands": c[k]} for k in order if c.get(k)]
	return series_chart(data, "severity", "brands")


def _summary(rows):
	breached = sum(1 for r in rows if r.get("severity") == "overdue")
	return [
		{"label": _("Brands"), "value": len(rows), "indicator": "blue"},
		{
			"label": _("SLA Breached"),
			"value": breached,
			"indicator": "red" if breached else "green",
		},
	]
