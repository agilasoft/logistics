# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors

from __future__ import unicode_literals

import frappe
from frappe import _

from logistics.control_tower.api import get_pipeline_summary


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("organization"):
		frappe.throw(_("Organization is required"))

	cond = ["organization = %s"]
	vals = [filters.organization]
	if filters.get("category"):
		cond.append("category = %s")
		vals.append(filters.category)
	rows = frappe.db.sql(
		"""
		SELECT name, client_name, customer, category, stage,
		       expected_close_date, estimated_revenue, estimated_gp,
		       probability_pct, weighted_gp, owner_employee
		FROM `tabPipeline Entry`
		WHERE {where}
		ORDER BY expected_close_date ASC, weighted_gp DESC
		""".format(where=" AND ".join(cond)),
		tuple(vals),
		as_dict=True,
	)

	columns = [
		{"fieldname": "name", "label": _("Name"), "fieldtype": "Link", "options": "Pipeline Entry", "width": 130},
		{"fieldname": "client_name", "label": _("Client"), "fieldtype": "Data", "width": 220},
		{"fieldname": "category", "label": _("Category"), "fieldtype": "Data", "width": 120},
		{"fieldname": "stage", "label": _("Stage"), "fieldtype": "Data", "width": 110},
		{"fieldname": "expected_close_date", "label": _("Expected Close"), "fieldtype": "Date", "width": 120},
		{"fieldname": "estimated_revenue", "label": _("Est. Revenue"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "estimated_gp", "label": _("Est. GP"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "probability_pct", "label": _("Prob %"), "fieldtype": "Percent", "width": 90},
		{"fieldname": "weighted_gp", "label": _("Weighted GP"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "owner_employee", "label": _("Owner"), "fieldtype": "Link", "options": "Employee", "width": 160},
	]

	summary = get_pipeline_summary(filters.organization, filters.get("category"))
	chart = {
		"data": {
			"labels": [s["stage"] for s in summary],
			"datasets": [
				{"name": _("Weighted GP"), "values": [s["weighted_gp"] for s in summary]},
				{"name": _("Estimated GP"), "values": [s["estimated_gp"] for s in summary]},
			],
		},
		"type": "bar",
		"title": _("Pipeline by Stage"),
	}
	return columns, rows, None, chart
