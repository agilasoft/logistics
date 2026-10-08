# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""AFCT Module Snapshot — Open vs Handled by module for the control tower chart."""

from __future__ import unicode_literals

from frappe import _

from logistics.air_freight.afct_report_utils import normalize_filters
from logistics.air_freight.air_freight_control_tower import module_snapshot_rows


def execute(filters=None):
	filters = normalize_filters(filters)
	columns = get_columns()
	data = module_snapshot_rows(filters)
	chart = get_chart(data)
	open_total = int(sum(r.get("open") or 0 for r in data))
	handled_total = int(sum(r.get("handled") or 0 for r in data))
	summary = [
		{"label": _("Open"), "value": open_total, "datatype": "Int", "indicator": "Blue"},
		{"label": _("Handled"), "value": handled_total, "datatype": "Int", "indicator": "Green"},
	]
	return columns, data, None, chart, summary


def get_columns():
	return [
		{"fieldname": "module", "label": _("Module"), "fieldtype": "Data", "width": 180},
		{"fieldname": "open", "label": _("Open"), "fieldtype": "Int", "width": 100},
		{"fieldname": "open_avg_age", "label": _("Avg age"), "fieldtype": "Float", "width": 110},
		{"fieldname": "handled", "label": _("Handled"), "fieldtype": "Int", "width": 110},
	]


def get_chart(data):
	return {
		"data": {
			"labels": [r.get("module") or "" for r in data],
			"datasets": [
				{"name": _("Open"), "values": [r.get("open") or 0 for r in data]},
				{"name": _("Handled"), "values": [r.get("handled") or 0 for r in data]},
			],
		},
		"type": "bar",
		"title": _("Open vs Handled"),
	}
