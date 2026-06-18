# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors

from __future__ import unicode_literals

import frappe
from frappe import _

from logistics.control_tower.api import get_top_n


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("organization"):
		frappe.throw(_("Organization is required"))
	n = int(filters.get("limit_n") or 5)
	data = get_top_n(filters.organization, "outsourced_trucker", n=n, fiscal_year=filters.get("fiscal_year_yyyy"))
	columns = [
		{"fieldname": "label", "label": _("Trucker (Supplier)"), "fieldtype": "Link", "options": "Supplier", "width": 240},
		{"fieldname": "value", "label": _("Outsourced Jobs (#)"), "fieldtype": "Int", "width": 160},
	]
	rows = [{"label": d["label"], "value": int(d["value"])} for d in data]
	chart = {
		"data": {
			"labels": [d["label"] for d in data],
			"datasets": [{"name": _("Outsourced Jobs"), "values": [d["value"] for d in data]}],
		},
		"type": "bar",
		"title": _("Top {0} Outsourced Truckers").format(n),
	}
	return columns, rows, None, chart
