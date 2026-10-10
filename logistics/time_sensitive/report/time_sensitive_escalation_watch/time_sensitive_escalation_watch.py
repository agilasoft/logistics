# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Operations: cases that need escalation — breach, missed checkpoint, or no acknowledgement."""

from frappe import _
from frappe.utils import now_datetime

from logistics.analytics_reports.bootstrap import tally_chart
from logistics.time_sensitive.ts_reports import escalation_watch_rows, fetch_cases


def execute(filters=None):
	filters = dict(filters or {})
	filters["open_only"] = 1
	now = now_datetime()
	columns = _columns()
	rows = escalation_watch_rows(fetch_cases(filters), now)
	if filters.get("watch_reason"):
		rows = [row for row in rows if row.get("watch_reason") == filters.get("watch_reason")]
	chart = tally_chart(rows, "watch_reason", dataset_label=_("Cases"))
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
		{"label": _("Watch"), "fieldname": "watch_reason", "fieldtype": "Data", "width": 150},
		{"label": _("SLA"), "fieldname": "sla_status", "fieldtype": "Data", "width": 100},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
		{"label": _("Severity"), "fieldname": "severity", "fieldtype": "Data", "width": 90},
		{"label": _("Deadline"), "fieldname": "critical_deadline", "fieldtype": "Datetime", "width": 150},
		{"label": _("Remaining (h)"), "fieldname": "remaining_hours", "fieldtype": "Int", "width": 120},
		{"label": _("Response Due"), "fieldname": "response_due_on", "fieldtype": "Datetime", "width": 150},
		{"label": _("Next Checkpoint"), "fieldname": "next_checkpoint", "fieldtype": "Datetime", "width": 150},
		{"label": _("Coordinator"), "fieldname": "coordinator", "fieldtype": "Link", "options": "User", "width": 140},
		{
			"label": _("Escalation Contact"),
			"fieldname": "escalation_contact",
			"fieldtype": "Link",
			"options": "User",
			"width": 150,
		},
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 140},
	]


def _summary(rows):
	breach = sum(1 for row in rows if row.get("watch_reason") == "Deadline breach")
	at_risk = sum(1 for row in rows if row.get("watch_reason") == "At risk")
	return [
		{"label": _("Watching"), "value": len(rows), "indicator": "blue"},
		{"label": _("Deadline Breach"), "value": breach, "indicator": "red" if breach else "green"},
		{"label": _("At Risk"), "value": at_risk, "indicator": "orange" if at_risk else "green"},
	]
