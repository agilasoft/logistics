# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
"""CT GP Summary - GP YTD / Prior / Target / vs Target % + 3-year compare."""

from __future__ import unicode_literals

import frappe
from frappe import _

from logistics.control_tower.api import get_gp_summary


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("organization"):
		frappe.throw(_("Organization is required"))
	summary = get_gp_summary(filters.organization, filters.get("fiscal_year_yyyy"))

	columns = [
		{"fieldname": "metric", "label": _("Metric"), "fieldtype": "Data", "width": 280},
		{"fieldname": "value", "label": _("Value (PHP)"), "fieldtype": "Currency", "width": 200},
	]
	year = summary["fiscal_year"]
	rows = [
		{"metric": _("Gross Profit ({0} YTD)").format(year), "value": summary["gp_ytd"]},
		{"metric": _("Gross Profit ({0} YTD)").format(year - 1), "value": summary["gp_prior_ytd"]},
		{"metric": _("Gross Profit ({0} YTD)").format(year - 2), "value": summary["gp_prior_prior_ytd"]},
		{"metric": _("Gross Profit ({0} Target)").format(year), "value": summary["gp_target"]},
		{"metric": _("GP vs Target %"), "value": summary["gp_vs_target_pct"]},
	]
	chart = {
		"data": {
			"labels": [str(b["year"]) for b in summary["breakdown"]] + [_("Target")],
			"datasets": [
				{
					"name": _("Gross Profit (PHP)"),
					"values": [b["gp"] for b in summary["breakdown"]] + [summary["gp_target"]],
				}
			],
		},
		"type": "bar",
		"title": _("GP 3-Year Compare vs Target ({0})").format(filters.organization),
	}
	report_summary = [
		{"label": _("GP YTD"), "value": summary["gp_ytd"], "datatype": "Currency", "currency": "PHP", "indicator": "Green"},
		{"label": _("GP Prior YTD"), "value": summary["gp_prior_ytd"], "datatype": "Currency", "currency": "PHP", "indicator": "Blue"},
		{"label": _("GP Target"), "value": summary["gp_target"], "datatype": "Currency", "currency": "PHP", "indicator": "Orange"},
		{"label": _("vs Target %"), "value": summary["gp_vs_target_pct"], "datatype": "Percent", "indicator": "Grey"},
	]
	return columns, rows, None, chart, report_summary
