# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors

from __future__ import unicode_literals

import frappe
from frappe import _

from logistics.control_tower.api import get_handling_in_out


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("organization"):
		frappe.throw(_("Organization is required"))
	data = get_handling_in_out(filters.organization, fiscal_year=filters.get("fiscal_year_yyyy"))
	columns = [
		{"fieldname": "period", "label": _("Period"), "fieldtype": "Data", "width": 160},
		{"fieldname": "inbound", "label": _("Handling In (Putaway)"), "fieldtype": "Int", "width": 180},
		{"fieldname": "outbound", "label": _("Handling Out (Pick)"), "fieldtype": "Int", "width": 180},
	]
	rows = [{"period": d["period"], "inbound": d["inbound"], "outbound": d["outbound"]} for d in data]
	chart = {
		"data": {
			"labels": [d["period"] for d in data],
			"datasets": [
				{"name": _("Handling In"), "values": [d["inbound"] for d in data]},
				{"name": _("Handling Out"), "values": [d["outbound"] for d in data]},
			],
		},
		"type": "bar",
		"title": _("Handling In and Out"),
	}
	return columns, rows, None, chart
