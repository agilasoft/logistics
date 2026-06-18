# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors

from __future__ import unicode_literals

import frappe
from frappe import _

from logistics.control_tower.api import get_trips_per_month


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("organization"):
		frappe.throw(_("Organization is required"))
	data = get_trips_per_month(filters.organization, fiscal_year=filters.get("fiscal_year_yyyy"))
	columns = [
		{"fieldname": "period", "label": _("Period (YYYY-MM)"), "fieldtype": "Data", "width": 160},
		{"fieldname": "trips", "label": _("Trips"), "fieldtype": "Int", "width": 120},
	]
	rows = [{"period": d["period"], "trips": d["trips"]} for d in data]
	chart = {
		"data": {
			"labels": [d["period"] for d in data],
			"datasets": [{"name": _("Trips"), "values": [d["trips"] for d in data]}],
		},
		"type": "bar",
		"title": _("Trips per Month"),
	}
	return columns, rows, None, chart
