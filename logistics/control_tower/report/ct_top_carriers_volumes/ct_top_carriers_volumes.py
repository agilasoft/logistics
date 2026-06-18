# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
"""CT Top Carriers Volumes - TEU / CBM / CHW."""

from __future__ import unicode_literals

import frappe
from frappe import _

from logistics.control_tower.api import get_top_n


METRIC_TO_DIM = {
	"Sea FCL (TEU)": ("carrier_sea_fcl_teu", "Shipping Line", "TEU"),
	"Sea LCL (CBM)": ("carrier_sea_lcl_cbm", "Shipping Line", "CBM"),
	"Air (CHW)": ("carrier_air_chw", "Airline", "Chargeable Weight"),
	"Airline (Count)": ("airline", "Airline", "Shipments"),
}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("organization"):
		frappe.throw(_("Organization is required"))
	metric = filters.get("metric") or "Sea FCL (TEU)"
	dim, label, unit = METRIC_TO_DIM.get(metric) or METRIC_TO_DIM["Sea FCL (TEU)"]
	n = int(filters.get("limit_n") or 5)
	data = get_top_n(filters.organization, dim, n=n, fiscal_year=filters.get("fiscal_year_yyyy"))
	options = "Shipping Line" if "Sea" in metric else "Airline"
	columns = [
		{"fieldname": "label", "label": label, "fieldtype": "Link", "options": options, "width": 240},
		{"fieldname": "value", "label": unit, "fieldtype": "Float", "width": 160},
	]
	rows = [{"label": d["label"], "value": d["value"]} for d in data]
	chart = {
		"data": {
			"labels": [d["label"] for d in data],
			"datasets": [{"name": unit, "values": [d["value"] for d in data]}],
		},
		"type": "bar",
		"title": _("Top {0} Carriers ({1})").format(n, metric),
	}
	return columns, rows, None, chart
