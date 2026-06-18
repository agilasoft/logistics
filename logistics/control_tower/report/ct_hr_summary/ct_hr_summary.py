# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt, nowdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	year = int(filters.get("fiscal_year_yyyy") or nowdate()[:4])
	ys, ye = "{0}-01-01".format(year), "{0}-12-31".format(year)

	open_vacancies = frappe.db.count("HR Vacancy", filters={"status": ["in", ["Open", "Interviewing", "Offered"]]}) or 0
	turnover_events = frappe.db.count("HR Turnover Event", filters={"exit_date": ["between", [ys, ye]]}) or 0
	tardiness = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(tardiness_minutes), 0) AS m,
		       COALESCE(SUM(ot_hours), 0) AS h
		FROM `tabHR Tardiness OT Entry`
		WHERE period BETWEEN %s AND %s
		""",
		(ys, ye),
	)
	tardiness_min = flt(tardiness[0][0]) if tardiness else 0
	ot_hours = flt(tardiness[0][1]) if tardiness else 0
	labor = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(actual_amount), 0) AS actual,
		       COALESCE(SUM(budget_amount), 0) AS budget
		FROM `tabHR Labor Cost Period`
		WHERE period BETWEEN %s AND %s
		""",
		(ys, ye),
	)
	actual = flt(labor[0][0]) if labor else 0
	budget = flt(labor[0][1]) if labor else 0
	variance_pct = ((actual - budget) / budget * 100.0) if budget else 0.0

	# Headcount proxy from ERPNext Employee, for turnover-rate denominator
	headcount = frappe.db.count("Employee", filters={"status": "Active"}) if frappe.db.exists("DocType", "Employee") else 0
	turnover_rate = (turnover_events / headcount * 100.0) if headcount else 0.0

	columns = [
		{"fieldname": "metric", "label": _("Metric"), "fieldtype": "Data", "width": 280},
		{"fieldname": "value", "label": _("Value"), "fieldtype": "Float", "width": 180},
	]
	rows = [
		{"metric": _("Open Vacancies"), "value": open_vacancies},
		{"metric": _("Turnover Events (YTD)"), "value": turnover_events},
		{"metric": _("Turnover Rate % (YTD)"), "value": flt(turnover_rate, 2)},
		{"metric": _("Tardiness Minutes (YTD)"), "value": tardiness_min},
		{"metric": _("OT Hours (YTD)"), "value": ot_hours},
		{"metric": _("Labor Cost Actual (YTD)"), "value": actual},
		{"metric": _("Labor Cost Budget (YTD)"), "value": budget},
		{"metric": _("Labor Cost Variance %"), "value": flt(variance_pct, 2)},
	]
	chart = {
		"data": {
			"labels": [_("Actual"), _("Budget")],
			"datasets": [{"name": _("Labor Cost"), "values": [actual, budget]}],
		},
		"type": "bar",
		"title": _("Labor Cost - Actual vs Budget"),
	}
	report_summary = [
		{"label": _("Open Vacancies"), "value": open_vacancies, "datatype": "Int", "indicator": "Orange"},
		{"label": _("Turnover Rate %"), "value": flt(turnover_rate, 2), "datatype": "Percent", "indicator": "Red"},
		{"label": _("Labor Variance %"), "value": flt(variance_pct, 2), "datatype": "Percent", "indicator": "Grey"},
	]
	return columns, rows, None, chart, report_summary
