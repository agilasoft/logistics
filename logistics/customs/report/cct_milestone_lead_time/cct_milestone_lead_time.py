# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""CCT Milestone Lead Time — drill-down for Avg Lead Time / Milestone KPI."""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt

from logistics.customs.cct_report_utils import date_bounds, dim_clauses, normalize_filters, unloco_clause

DECLARATION = "Declaration"
DECLARATION_MILESTONE = "Declaration Milestone"


def execute(filters=None):
	filters = normalize_filters(filters)
	if not frappe.db.exists("DocType", DECLARATION_MILESTONE):
		return get_columns(), [], _("Declaration Milestone DocType is not installed.")

	columns = get_columns()
	data = get_data(filters)
	lead_times = [flt(r.get("lead_time_days")) for r in data]
	avg_lt = round(sum(lead_times) / len(lead_times), 1) if lead_times else 0
	summary = [
		{"label": _("Milestones"), "value": len(data), "datatype": "Int", "indicator": "Blue"},
		{"label": _("Avg Lead Time (days)"), "value": avg_lt, "datatype": "Float", "indicator": "Orange"},
	]
	chart = get_chart(data)
	return columns, data, None, chart, summary


def get_columns():
	return [
		{"fieldname": "declaration", "label": _("Declaration"), "fieldtype": "Link", "options": "Declaration", "width": 150},
		{"fieldname": "milestone", "label": _("Milestone"), "fieldtype": "Data", "width": 160},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
		{"fieldname": "planned_start", "label": _("Planned Start"), "fieldtype": "Datetime", "width": 140},
		{"fieldname": "planned_end", "label": _("Planned End"), "fieldtype": "Datetime", "width": 140},
		{"fieldname": "actual_start", "label": _("Actual Start"), "fieldtype": "Datetime", "width": 140},
		{"fieldname": "actual_end", "label": _("Actual End"), "fieldtype": "Datetime", "width": 140},
		{"fieldname": "lead_time_days", "label": _("Lead Time (days)"), "fieldtype": "Float", "width": 130},
		{"fieldname": "customs_authority", "label": _("Customs Authority"), "fieldtype": "Link", "options": "Customs Authority", "width": 160},
		{"fieldname": "company", "label": _("Company"), "fieldtype": "Link", "options": "Company", "width": 150},
		{"fieldname": "branch", "label": _("Branch"), "fieldtype": "Link", "options": "Branch", "width": 120},
		{"fieldname": "job_status", "label": _("Job Status"), "fieldtype": "Data", "width": 110},
	]


def get_data(filters):
	from_date, to_date = date_bounds(filters)
	dim_c, dim_v = dim_clauses(filters, prefix="p.")
	unloco_c, unloco_v = unloco_clause(filters, prefix="p.")
	extra_parts = list(dim_c) + list(unloco_c) + ["p.declaration_date BETWEEN %s AND %s"]
	values = [DECLARATION] + list(dim_v) + list(unloco_v) + [from_date, to_date]
	extra = " AND " + " AND ".join(extra_parts)

	rows = frappe.db.sql(
		"""
		SELECT
			p.name AS declaration,
			c.milestone,
			c.status,
			c.planned_start,
			c.planned_end,
			c.actual_start,
			c.actual_end,
			(
				TIMESTAMPDIFF(
					SECOND,
					COALESCE(c.planned_end, c.planned_start),
					COALESCE(c.actual_end, c.actual_start)
				) / 86400.0
			) AS lead_time_days,
			p.customs_authority,
			p.company,
			p.branch,
			p.job_status
		FROM `tab{child}` c
		JOIN `tab{parent}` p ON p.name = c.parent
		WHERE c.parenttype = %s
		  AND (c.actual_end IS NOT NULL OR c.actual_start IS NOT NULL)
		  AND (c.planned_end IS NOT NULL OR c.planned_start IS NOT NULL)
		  {extra}
		ORDER BY ABS(
			TIMESTAMPDIFF(
				SECOND,
				COALESCE(c.planned_end, c.planned_start),
				COALESCE(c.actual_end, c.actual_start)
			)
		) DESC
		LIMIT 5000
		""".format(child=DECLARATION_MILESTONE, parent=DECLARATION, extra=extra),
		tuple(values),
		as_dict=True,
	)
	for row in rows:
		row.lead_time_days = round(flt(row.lead_time_days), 2)
	return rows


def get_chart(data):
	by_ms = {}
	counts = {}
	for row in data:
		key = row.get("milestone") or _("Unknown")
		by_ms[key] = by_ms.get(key, 0) + flt(row.get("lead_time_days"))
		counts[key] = counts.get(key, 0) + 1
	labels = sorted(by_ms.keys(), key=lambda key: abs(by_ms[key] / counts[key]), reverse=True)[:12]
	return {
		"data": {
			"labels": labels,
			"datasets": [{
				"name": _("Avg Lead Time (days)"),
				"values": [round(by_ms[label] / counts[label], 1) for label in labels],
			}],
		},
		"type": "bar",
		"title": _("Avg Lead Time by Milestone"),
	}
