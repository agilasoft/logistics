# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Service Modes: time-sensitive documents on the modes listed in the workspace."""

from frappe import _

from logistics.analytics_reports.bootstrap import series_chart
from logistics.time_sensitive.ts_reports import count_service_modes, service_mode_rows


def execute(filters=None):
	filters = filters or {}
	columns = _columns()
	rows = service_mode_rows(count_service_modes(filters))
	if filters.get("service_mode"):
		rows = [row for row in rows if row.get("service_mode") == filters.get("service_mode")]
	chart = series_chart(rows, "service_mode", "documents", chart_type="pie")
	return columns, rows, None, chart, _summary(rows)


def _columns():
	return [
		{"label": _("Service Mode"), "fieldname": "service_mode", "fieldtype": "Data", "width": 160},
		{"label": _("Document"), "fieldname": "doctype", "fieldtype": "Data", "width": 160},
		{"label": _("Service Type"), "fieldname": "service_type", "fieldtype": "Data", "width": 120},
		{"label": _("Documents"), "fieldname": "documents", "fieldtype": "Int", "width": 110},
		{"label": _("Cases"), "fieldname": "cases", "fieldtype": "Int", "width": 90},
	]


def _summary(rows):
	documents = sum(int(row.get("documents") or 0) for row in rows)
	cases = sum(int(row.get("cases") or 0) for row in rows)
	active_modes = sum(1 for row in rows if int(row.get("documents") or 0))
	return [
		{"label": _("Documents"), "value": documents, "indicator": "blue"},
		{"label": _("Cases"), "value": cases, "indicator": "blue"},
		{"label": _("Modes In Use"), "value": active_modes, "indicator": "green" if active_modes else "orange"},
	]
