# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
"""CT Top Agents Volumes - Freight Agent by TEU / CBM / CHW."""

from __future__ import unicode_literals

import frappe
from frappe import _

from logistics.control_tower.api import get_top_n


METRIC_TO_DIM = {
	"Sea FCL (TEU)": ("agent_sea_fcl_teu", "TEU"),
	"Sea LCL (CBM)": ("agent_sea_lcl_cbm", "CBM"),
	"Air (CHW)": ("agent_air_chw", "Chargeable Weight"),
}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("organization"):
		frappe.throw(_("Organization is required"))
	metric = filters.get("metric") or "Sea FCL (TEU)"
	dim, unit = METRIC_TO_DIM.get(metric) or METRIC_TO_DIM["Sea FCL (TEU)"]
	n = int(filters.get("limit_n") or 5)
	data = get_top_n(filters.organization, dim, n=n, fiscal_year=filters.get("fiscal_year_yyyy"))
	columns = [
		{"fieldname": "label", "label": _("Freight Agent"), "fieldtype": "Link", "options": "Freight Agent", "width": 240},
		{"fieldname": "value", "label": unit, "fieldtype": "Float", "width": 160},
	]
	rows = [{"label": d["label"], "value": d["value"]} for d in data]
	chart = {
		"data": {
			"labels": [d["label"] for d in data],
			"datasets": [{"name": unit, "values": [d["value"] for d in data]}],
		},
		"type": "bar",
		"title": _("Top {0} Agents ({1})").format(n, metric),
	}
	return columns, rows, None, chart
