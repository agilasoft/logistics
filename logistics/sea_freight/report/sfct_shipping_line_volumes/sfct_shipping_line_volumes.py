# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""SFCT Shipping Line Volumes — drill-down for Top Shipping Lines chart."""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt

from logistics.sea_freight.sfct_report_utils import (
	dim_clauses,
	normalize_filters,
	unloco_clause,
	date_bounds,
)


def execute(filters=None):
	filters = normalize_filters(filters)
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	summary = [
		{"label": _("Shipping Lines"), "value": len(data), "datatype": "Int", "indicator": "Blue"},
		{
			"label": _("Shipments"),
			"value": int(sum(flt(r.get("shipment_count")) for r in data)),
			"datatype": "Int",
			"indicator": "Green",
		},
		{"label": _("FY"), "value": filters.fiscal_year, "datatype": "Int"},
	]
	return columns, data, None, chart, summary


def get_columns():
	return [
		{"fieldname": "shipping_line", "label": _("Shipping Line"), "fieldtype": "Link", "options": "Shipping Line", "width": 160},
		{"fieldname": "shipment_count", "label": _("Shipments"), "fieldtype": "Int", "width": 110},
		{"fieldname": "total_weight", "label": _("Total Weight"), "fieldtype": "Float", "width": 120},
		{"fieldname": "chargeable", "label": _("Chargeable"), "fieldtype": "Float", "width": 120},
		{"fieldname": "open_count", "label": _("Open"), "fieldtype": "Int", "width": 90},
		{"fieldname": "pct_of_total", "label": _("% of Total"), "fieldtype": "Percent", "width": 100},
	]


def get_data(filters):
	from_date, to_date = date_bounds(filters)
	dim_c, dim_v = dim_clauses(filters)
	unloco_c, unloco_v = unloco_clause(filters)
	conditions = dim_c + unloco_c + [
		"booking_date BETWEEN %s AND %s",
		"IFNULL(shipping_line, '') != ''",
	]
	values = dim_v + unloco_v + [from_date, to_date]
	if filters.shipping_line:
		conditions.append("shipping_line = %s")
		values.append(filters.shipping_line)

	where = " AND ".join(conditions)
	rows = frappe.db.sql(
		"""
		SELECT
			shipping_line,
			COUNT(*) AS shipment_count,
			SUM(IFNULL(weight, 0)) AS total_weight,
			SUM(IFNULL(chargeable, 0)) AS chargeable,
			SUM(CASE WHEN job_status NOT IN ('Completed', 'Closed', 'Cancelled') THEN 1 ELSE 0 END) AS open_count
		FROM `tabSea Shipment`
		WHERE {where}
		GROUP BY shipping_line
		ORDER BY shipment_count DESC
		LIMIT %s
		""".format(where=where),
		tuple(values + [filters.limit]),
		as_dict=True,
	)
	total = sum(flt(r.shipment_count) for r in rows) or 1
	for r in rows:
		r.pct_of_total = round((flt(r.shipment_count) / total) * 100.0, 1)
		r.total_weight = round(flt(r.total_weight), 2)
		r.chargeable = round(flt(r.chargeable), 2)
	return rows


def get_chart(data):
	return {
		"data": {
			"labels": [r.get("shipping_line") or "" for r in data],
			"datasets": [{
				"name": _("Shipments"),
				"values": [flt(r.get("shipment_count")) for r in data],
			}],
		},
		"type": "bar",
		"title": _("Top Shipping Lines by Shipments"),
	}
