# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
"""CT Jobs KPI - Open / Avg Age / Handled / Avg Lead Time / Returned Billings."""

from __future__ import unicode_literals

import frappe
from frappe import _

from logistics.control_tower.api import get_jobs_kpi


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("organization"):
		frappe.throw(_("Organization is required"))
	modules = None
	if filters.get("modules"):
		modules = [m.strip() for m in str(filters.modules).split(",") if m.strip()]
	kpi = get_jobs_kpi(filters.organization, modules=modules, fiscal_year=filters.get("fiscal_year_yyyy"))

	columns = [
		{"fieldname": "module", "label": _("Module"), "fieldtype": "Data", "width": 180},
		{"fieldname": "open", "label": _("Open Jobs"), "fieldtype": "Int", "width": 110},
		{"fieldname": "open_avg_age", "label": _("Avg Age (days)"), "fieldtype": "Float", "width": 130},
		{"fieldname": "handled", "label": _("Jobs Handled"), "fieldtype": "Int", "width": 130},
	]
	rows = list(kpi.get("by_module") or [])
	rows.append({
		"module": _("TOTAL"),
		"open": kpi.get("open_job_files_count", 0),
		"open_avg_age": kpi.get("avg_age_open_jobs", 0),
		"handled": kpi.get("jobs_handled_count", 0),
	})
	report_summary = [
		{"label": _("Open Job Files"), "value": kpi["open_job_files_count"], "datatype": "Int", "indicator": "Orange"},
		{"label": _("Avg Age (days)"), "value": kpi["avg_age_open_jobs"], "datatype": "Float", "indicator": "Grey"},
		{"label": _("Jobs Handled (YTD)"), "value": kpi["jobs_handled_count"], "datatype": "Int", "indicator": "Blue"},
		{"label": _("Avg Lead Time (days)"), "value": kpi["avg_lead_time_per_milestone"], "datatype": "Float", "indicator": "Grey"},
		{"label": _("Returned Billings (YTD)"), "value": kpi["returned_billings_count"], "datatype": "Int", "indicator": "Red"},
	]
	chart = {
		"data": {
			"labels": [r["module"] for r in (kpi.get("by_module") or [])],
			"datasets": [
				{"name": _("Open"), "values": [r["open"] for r in (kpi.get("by_module") or [])]},
				{"name": _("Handled"), "values": [r["handled"] for r in (kpi.get("by_module") or [])]},
			],
		},
		"type": "bar",
		"title": _("Jobs KPI by Module"),
	}
	return columns, rows, None, chart, report_summary
