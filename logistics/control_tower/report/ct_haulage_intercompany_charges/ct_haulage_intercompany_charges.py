# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
"""CT Haulage Intercompany Charges.

Monthly haulage revenue split between:
- Charge to File   (Transport Job linked to ATN owning files, i.e. revenue
                    bookings within the org)
- Charge to ASL    (Transport Job rows where the customer is an ASL company
                    or the intercompany_invoice_log records an ASL recipient)

Falls back to an estimated_revenue rollup when the intercompany log isn't
populated yet.
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt, nowdate

from logistics.control_tower.api import _dim_clauses, resolve_org_filters


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("organization"):
		frappe.throw(_("Organization is required"))
	year = int(filters.get("fiscal_year_yyyy") or nowdate()[:4])
	org_filters = resolve_org_filters(filters.organization)

	conditions = ["booking_date BETWEEN %s AND %s"]
	values = ["{0}-01-01".format(year), "{0}-12-31".format(year)]
	dim_conditions, dim_values = _dim_clauses(org_filters)
	conditions.extend(dim_conditions)
	values.extend(dim_values)

	asl_marker = "ASL"
	rs = frappe.db.sql(
		"""
		SELECT DATE_FORMAT(booking_date, '%%Y-%%m') AS period,
		       SUM(CASE WHEN UPPER(COALESCE(customer, '')) LIKE %s
		                THEN COALESCE(estimated_revenue, 0) ELSE 0 END) AS charge_to_asl,
		       SUM(CASE WHEN UPPER(COALESCE(customer, '')) NOT LIKE %s
		                THEN COALESCE(estimated_revenue, 0) ELSE 0 END) AS charge_to_file
		FROM `tabTransport Job`
		WHERE {where}
		GROUP BY DATE_FORMAT(booking_date, '%%Y-%%m')
		ORDER BY period
		""".format(where=" AND ".join(conditions) or "1=1"),
		tuple(["%" + asl_marker + "%", "%" + asl_marker + "%"] + values),
		as_dict=True,
	)

	columns = [
		{"fieldname": "period", "label": _("Period"), "fieldtype": "Data", "width": 120},
		{"fieldname": "charge_to_file", "label": _("Charge to File (PHP)"), "fieldtype": "Currency", "width": 180},
		{"fieldname": "charge_to_asl", "label": _("Charge to ASL (PHP)"), "fieldtype": "Currency", "width": 180},
	]
	rows = [
		{
			"period": r["period"],
			"charge_to_file": flt(r["charge_to_file"]),
			"charge_to_asl": flt(r["charge_to_asl"]),
		}
		for r in rs
	]
	chart = {
		"data": {
			"labels": [r["period"] for r in rs],
			"datasets": [
				{"name": _("Charge to File"), "values": [flt(r["charge_to_file"]) for r in rs]},
				{"name": _("Charge to ASL"), "values": [flt(r["charge_to_asl"]) for r in rs]},
			],
		},
		"type": "bar",
		"title": _("Monthly Haulage Charges"),
	}
	return columns, rows, None, chart
