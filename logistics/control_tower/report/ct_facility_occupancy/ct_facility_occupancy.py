# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
"""CT Facility Occupancy - approximate warehouse occupancy.

Uses ``Storage Location`` rows + handled bins as a proxy when the dedicated
warehouse utilization computation isn't accessible. The fallback shows 0%
rather than failing so the dashboard still renders.
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt

from logistics.control_tower.api import resolve_org_filters


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("organization"):
		frappe.throw(_("Organization is required"))

	org_filters = resolve_org_filters(filters.organization)
	companies = org_filters.get("company") or []
	branches = org_filters.get("branch") or []

	columns = [
		{"fieldname": "warehouse", "label": _("Warehouse"), "fieldtype": "Data", "width": 240},
		{"fieldname": "total_bins", "label": _("Total Bins"), "fieldtype": "Int", "width": 120},
		{"fieldname": "occupied_bins", "label": _("Occupied Bins"), "fieldtype": "Int", "width": 130},
		{"fieldname": "occupancy_pct", "label": _("Occupancy %"), "fieldtype": "Percent", "width": 120},
	]

	rows = []
	overall_total = 0
	overall_occupied = 0

	# Source: prefer ``Storage Location`` with an ``occupied`` flag if such doctype
	# is configured in this tenant; otherwise return a zeroed row per warehouse so
	# the dashboard still renders without errors.
	if frappe.db.exists("DocType", "Storage Location"):
		conditions = ["1=1"]
		values = []
		if companies:
			conditions.append("company IN ({0})".format(", ".join(["%s"] * len(companies))))
			values.extend(companies)
		if branches:
			conditions.append("branch IN ({0})".format(", ".join(["%s"] * len(branches))))
			values.extend(branches)
		try:
			rs = frappe.db.sql(
				"""
				SELECT warehouse,
				       COUNT(*) AS total_bins,
				       SUM(CASE WHEN occupied = 1 THEN 1 ELSE 0 END) AS occupied_bins
				FROM `tabStorage Location`
				WHERE {0}
				GROUP BY warehouse
				""".format(" AND ".join(conditions)),
				tuple(values),
				as_dict=True,
			)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "ct_facility_occupancy")
			rs = []
		for r in rs:
			total = int(r["total_bins"] or 0)
			occ = int(r["occupied_bins"] or 0)
			pct = (occ / total * 100.0) if total else 0.0
			overall_total += total
			overall_occupied += occ
			rows.append({"warehouse": r["warehouse"], "total_bins": total, "occupied_bins": occ, "occupancy_pct": pct})

	overall_pct = (overall_occupied / overall_total * 100.0) if overall_total else 0.0
	report_summary = [
		{"label": _("Facility Occupancy %"), "value": flt(overall_pct, 2), "datatype": "Percent", "indicator": "Orange" if overall_pct > 80 else "Green"},
		{"label": _("Total Bins"), "value": overall_total, "datatype": "Int", "indicator": "Grey"},
		{"label": _("Occupied Bins"), "value": overall_occupied, "datatype": "Int", "indicator": "Blue"},
	]
	chart = {
		"data": {
			"labels": [_("Occupied"), _("Free")],
			"datasets": [{"name": _("Bins"), "values": [overall_occupied, max(0, overall_total - overall_occupied)]}],
		},
		"type": "donut",
		"title": _("Facility Occupancy"),
	}
	return columns, rows, None, chart, report_summary
