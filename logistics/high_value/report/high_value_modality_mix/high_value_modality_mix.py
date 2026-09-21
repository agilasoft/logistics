# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from frappe import _

from logistics.analytics_reports.bootstrap import series_chart
from logistics.high_value.hv_analytics import count_modality


def execute(filters=None):
	filters = filters or {}
	columns = [
		{"label": _("Modality"), "fieldname": "modality", "fieldtype": "Data", "width": 140},
		{"label": _("Doctype"), "fieldname": "doctype", "fieldtype": "Data", "width": 160},
		{"label": _("Documents"), "fieldname": "documents", "fieldtype": "Int", "width": 110},
	]
	rows = count_modality(filters)
	chart = series_chart(rows, "modality", "documents", chart_type="pie")
	total = sum(int(r.get("documents") or 0) for r in rows)
	summary = [{"label": _("HV Documents"), "value": total, "indicator": "blue"}]
	return columns, rows, None, chart, summary
