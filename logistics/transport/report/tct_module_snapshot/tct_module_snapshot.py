# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""TCT Module Snapshot — Open vs Handled for the control tower chart."""

from __future__ import unicode_literals

from frappe import _

from logistics.transport.tct_report_utils import normalize_filters
from logistics.transport.transport_control_tower import module_snapshot_rows


def execute(filters=None):
	filters = normalize_filters(filters)
	columns = get_columns()
	data = module_snapshot_rows(filters)
	chart = get_chart(data)
	open_total = int(sum(row.get("open") or 0 for row in data))
	handled_total = int(sum(row.get("handled") or 0 for row in data))
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
			"labels": [row.get("module") or "" for row in data],
			"datasets": [
				{"name": _("Open"), "values": [row.get("open") or 0 for row in data]},
				{"name": _("Handled"), "values": [row.get("handled") or 0 for row in data]},
			],
		},
		"type": "bar",
		"title": _("Open vs Handled"),
	}
