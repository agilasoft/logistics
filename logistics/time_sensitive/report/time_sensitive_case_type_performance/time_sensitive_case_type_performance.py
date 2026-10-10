# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Setup: case volume and SLA pressure by Time Sensitive Case Type."""

from frappe import _

from logistics.analytics_reports.bootstrap import bar_top_numeric
from logistics.time_sensitive.ts_reports import case_type_performance_rows, fetch_cases


def execute(filters=None):
	columns = _columns()
	rows = case_type_performance_rows(fetch_cases(filters))
	chart = bar_top_numeric(rows, "case_type_name", "cases", dataset_label=_("Cases"))
	return columns, rows, None, chart, _summary(rows)


def _columns():
	return [
		{
			"label": _("Case Type"),
			"fieldname": "case_type",
			"fieldtype": "Link",
			"options": "Time Sensitive Case Type",
			"width": 140,
		},
		{"label": _("Name"), "fieldname": "case_type_name", "fieldtype": "Data", "width": 180},
		{"label": _("Cases"), "fieldname": "cases", "fieldtype": "Int", "width": 90},
		{"label": _("Ongoing"), "fieldname": "ongoing", "fieldtype": "Int", "width": 100},
		{"label": _("Nearing Due"), "fieldname": "nearing_due", "fieldtype": "Int", "width": 120},
		{"label": _("Overdue"), "fieldname": "overdue", "fieldtype": "Int", "width": 100},
		{"label": _("Closed"), "fieldname": "closed", "fieldtype": "Int", "width": 90},
		{"label": _("Cancelled"), "fieldname": "cancelled", "fieldtype": "Int", "width": 100},
	]


def _summary(rows):
	overdue = sum(int(row.get("overdue") or 0) for row in rows)
	nearing = sum(int(row.get("nearing_due") or 0) for row in rows)
	return [
		{"label": _("Case Types"), "value": len(rows), "indicator": "blue"},
		{"label": _("Overdue"), "value": overdue, "indicator": "red" if overdue else "green"},
		{"label": _("Nearing Due"), "value": nearing, "indicator": "orange" if nearing else "green"},
	]
