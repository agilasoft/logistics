# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from frappe import _
from frappe.utils import nowdate

from logistics.analytics_reports.bootstrap import series_chart
from logistics.high_value.hv_analytics import (
	AGING_BUCKETS,
	apply_job_filters,
	load_report_context,
	sla_age_bucket,
	sort_jobs_by_sla,
)


def execute(filters=None):
	filters = filters or {}
	as_on = filters.get("as_on_date") or nowdate()
	columns = _columns()
	_brands, _quotes, jobs = load_report_context(filters)
	rows = []
	for j in sort_jobs_by_sla(apply_job_filters(jobs, filters)):
		row = dict(j)
		row["age_bucket"] = sla_age_bucket(j.get("sla_target_date"), as_on)
		row["jobs"] = 1
		rows.append(row)
	chart, summary = _chart_and_summary(rows)
	return columns, rows, None, chart, summary


def _columns():
	return [
		{
			"label": _("Job"),
			"fieldname": "name",
			"fieldtype": "Dynamic Link",
			"options": "doctype",
			"width": 140,
		},
		{"label": _("Doctype"), "fieldname": "doctype", "fieldtype": "Data", "width": 130},
		{"label": _("Modality"), "fieldname": "modality", "fieldtype": "Data", "width": 90},
		{"label": _("Brand"), "fieldname": "hv_brand", "fieldtype": "Link", "options": "HV Brands", "width": 110},
		{"label": _("Aging Bucket"), "fieldname": "age_bucket", "fieldtype": "Data", "width": 110},
		{"label": _("SLA"), "fieldname": "sla_status", "fieldtype": "Data", "width": 100},
		{"label": _("SLA Target"), "fieldname": "sla_target_date", "fieldtype": "Date", "width": 110},
		{"label": _("Status"), "fieldname": "job_status", "fieldtype": "Data", "width": 110},
		{"label": _("Owner"), "fieldname": "owner", "fieldtype": "Link", "options": "User", "width": 140},
		{
			"label": _("Sales Quote"),
			"fieldname": "sales_quote",
			"fieldtype": "Link",
			"options": "Sales Quote",
			"width": 130,
		},
		{"label": _("Jobs"), "fieldname": "jobs", "fieldtype": "Int", "width": 70, "hidden": 1},
	]


def _chart_and_summary(rows):
	totals = {b: 0 for b in AGING_BUCKETS}
	for r in rows:
		bucket = r.get("age_bucket") or "No target"
		totals[bucket] = totals.get(bucket, 0) + 1
	data = [{"age_bucket": b, "jobs": totals.get(b, 0)} for b in AGING_BUCKETS]
	chart = series_chart(data, "age_bucket", "jobs")
	overdue = totals.get("Overdue") or 0
	due_today = totals.get("Due today") or 0
	summary = [
		{"label": _("Open jobs"), "value": len(rows), "indicator": "blue"},
		{"label": _("Overdue"), "value": overdue, "indicator": "red" if overdue else "green"},
		{"label": _("Due today"), "value": due_today, "indicator": "orange" if due_today else "green"},
	]
	return chart, summary
