# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Operations: open Time Sensitive cases grouped by coordinator."""

from frappe import _

from logistics.analytics_reports.bootstrap import bar_top_numeric
from logistics.time_sensitive.ts_reports import coordinator_workload_rows, fetch_cases


def execute(filters=None):
	filters = dict(filters or {})
	filters["open_only"] = 1
	columns = _columns()
	rows = coordinator_workload_rows(fetch_cases(filters))
	chart = bar_top_numeric(rows, "coordinator_label", "open_cases", dataset_label=_("Open Cases"))
	return columns, rows, None, chart, _summary(rows)


def _columns():
	return [
		{"label": _("Coordinator"), "fieldname": "coordinator_label", "fieldtype": "Data", "width": 180},
		{"label": _("Open Cases"), "fieldname": "open_cases", "fieldtype": "Int", "width": 110},
		{"label": _("Ongoing"), "fieldname": "ongoing", "fieldtype": "Int", "width": 100},
		{"label": _("Nearing Due"), "fieldname": "nearing_due", "fieldtype": "Int", "width": 120},
		{"label": _("Overdue"), "fieldname": "overdue", "fieldtype": "Int", "width": 100},
		{"label": _("On Hold"), "fieldname": "on_hold", "fieldtype": "Int", "width": 100},
		{"label": _("Critical"), "fieldname": "critical", "fieldtype": "Int", "width": 90},
	]


def _summary(rows):
	overdue = sum(int(row.get("overdue") or 0) for row in rows)
	unassigned = sum(int(row.get("open_cases") or 0) for row in rows if not row.get("coordinator"))
	return [
		{"label": _("Coordinators"), "value": len(rows), "indicator": "blue"},
		{"label": _("Overdue Cases"), "value": overdue, "indicator": "red" if overdue else "green"},
		{"label": _("Unassigned"), "value": unassigned, "indicator": "orange" if unassigned else "green"},
	]
