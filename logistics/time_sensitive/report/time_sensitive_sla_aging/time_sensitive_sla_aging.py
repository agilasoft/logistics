# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Operations: how close open and historical cases are to the critical deadline."""

from frappe import _
from frappe.utils import now_datetime, nowdate

from logistics.analytics_reports.bootstrap import series_chart
from logistics.time_sensitive.ts_reports import AGING_BUCKETS, fetch_cases, sla_aging_rows


def execute(filters=None):
	filters = filters or {}
	as_on = filters.get("as_on_date") or nowdate()
	now = now_datetime()
	columns = _columns()
	rows = sla_aging_rows(fetch_cases(filters), as_on, now)
	if filters.get("age_bucket"):
		rows = [row for row in rows if row.get("age_bucket") == filters.get("age_bucket")]
	chart = series_chart(_bucket_chart_rows(rows), "age_bucket", "cases")
	return columns, rows, None, chart, _summary(rows)


def _columns():
	return [
		{
			"label": _("Case"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Time Sensitive Case",
			"width": 140,
		},
		{"label": _("Title"), "fieldname": "case_title", "fieldtype": "Data", "width": 180},
		{"label": _("Aging"), "fieldname": "age_bucket", "fieldtype": "Data", "width": 110},
		{"label": _("Remaining (h)"), "fieldname": "remaining_hours", "fieldtype": "Int", "width": 120},
		{"label": _("Deadline"), "fieldname": "critical_deadline", "fieldtype": "Datetime", "width": 150},
		{"label": _("SLA"), "fieldname": "sla_status", "fieldtype": "Data", "width": 100},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
		{"label": _("Severity"), "fieldname": "severity", "fieldtype": "Data", "width": 90},
		{"label": _("Type"), "fieldname": "case_type_name", "fieldtype": "Data", "width": 140},
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 140},
		{"label": _("Coordinator"), "fieldname": "coordinator", "fieldtype": "Link", "options": "User", "width": 140},
	]


def _bucket_chart_rows(rows):
	totals = {bucket: 0 for bucket in AGING_BUCKETS}
	for row in rows:
		bucket = row.get("age_bucket") or "No deadline"
		totals[bucket] = totals.get(bucket, 0) + 1
	return [{"age_bucket": bucket, "cases": totals.get(bucket, 0)} for bucket in AGING_BUCKETS]


def _summary(rows):
	overdue = sum(1 for row in rows if row.get("age_bucket") == "Overdue")
	due_today = sum(1 for row in rows if row.get("age_bucket") == "Due today")
	return [
		{"label": _("Cases"), "value": len(rows), "indicator": "blue"},
		{"label": _("Overdue"), "value": overdue, "indicator": "red" if overdue else "green"},
		{"label": _("Due today"), "value": due_today, "indicator": "orange" if due_today else "green"},
	]
