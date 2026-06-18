# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors

from __future__ import unicode_literals

import frappe
from frappe import _

from logistics.control_tower.api import get_risk_register_summary


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("organization"):
		frappe.throw(_("Organization is required"))

	cond = ["organization = %s"]
	vals = [filters.organization]
	if filters.get("status"):
		cond.append("status = %s")
		vals.append(filters.status)
	rows = frappe.db.sql(
		"""
		SELECT name, title, category, likelihood, impact, score, status,
		       target_close_date, owner_employee
		FROM `tabRisk Register Entry`
		WHERE {where}
		ORDER BY score DESC, target_close_date ASC
		""".format(where=" AND ".join(cond)),
		tuple(vals),
		as_dict=True,
	)

	columns = [
		{"fieldname": "name", "label": _("Name"), "fieldtype": "Link", "options": "Risk Register Entry", "width": 130},
		{"fieldname": "title", "label": _("Title"), "fieldtype": "Data", "width": 280},
		{"fieldname": "category", "label": _("Category"), "fieldtype": "Data", "width": 140},
		{"fieldname": "likelihood", "label": _("L"), "fieldtype": "Int", "width": 60},
		{"fieldname": "impact", "label": _("I"), "fieldtype": "Int", "width": 60},
		{"fieldname": "score", "label": _("Score"), "fieldtype": "Int", "width": 70},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 110},
		{"fieldname": "target_close_date", "label": _("Target Close"), "fieldtype": "Date", "width": 120},
		{"fieldname": "owner_employee", "label": _("Owner"), "fieldtype": "Link", "options": "Employee", "width": 160},
	]

	summary = get_risk_register_summary(filters.organization)
	chart = {
		"data": {
			"labels": [s["band"] for s in summary],
			"datasets": [{"name": _("Risks"), "values": [s["count"] for s in summary]}],
		},
		"type": "bar",
		"title": _("Risk Register Heatmap"),
	}
	return columns, rows, None, chart
