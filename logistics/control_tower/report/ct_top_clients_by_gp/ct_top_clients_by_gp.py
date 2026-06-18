# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
"""CT Top Clients by GP."""

from __future__ import unicode_literals

import frappe
from frappe import _

from logistics.control_tower.api import get_top_n


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("organization"):
		frappe.throw(_("Organization is required"))
	n = int(filters.get("limit_n") or 10)
	data = get_top_n(filters.organization, "customer", n=n, fiscal_year=filters.get("fiscal_year_yyyy"))
	columns = [
		{"fieldname": "label", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 280},
		{"fieldname": "value", "label": _("Gross Profit (PHP)"), "fieldtype": "Currency", "width": 200},
	]
	rows = [{"label": d["label"], "value": d["value"]} for d in data]
	chart = {
		"data": {
			"labels": [d["label"] for d in data],
			"datasets": [{"name": _("Gross Profit"), "values": [d["value"] for d in data]}],
		},
		"type": "bar",
		"title": _("Top {0} Clients by GP").format(n),
	}
	return columns, rows, None, chart
