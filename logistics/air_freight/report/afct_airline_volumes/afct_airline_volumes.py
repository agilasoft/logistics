# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""AFCT Airline Volumes — drill-down for Top Airlines chart."""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt

from logistics.air_freight.afct_report_utils import (
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
		{"label": _("Airlines"), "value": len(data), "datatype": "Int", "indicator": "Blue"},
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
		{"fieldname": "airline", "label": _("Airline"), "fieldtype": "Link", "options": "Airline", "width": 160},
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
		"IFNULL(airline, '') != ''",
	]
	values = dim_v + unloco_v + [from_date, to_date]
	if filters.airline:
		conditions.append("airline = %s")
		values.append(filters.airline)

	where = " AND ".join(conditions)
	rows = frappe.db.sql(
		"""
		SELECT
			airline,
			COUNT(*) AS shipment_count,
			SUM(IFNULL(weight, 0)) AS total_weight,
			SUM(IFNULL(chargeable, 0)) AS chargeable,
			SUM(CASE WHEN job_status NOT IN ('Completed', 'Closed', 'Cancelled') THEN 1 ELSE 0 END) AS open_count
		FROM `tabAir Shipment`
		WHERE {where}
		GROUP BY airline
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
			"labels": [r.get("airline") or "" for r in data],
			"datasets": [{
				"name": _("Shipments"),
				"values": [flt(r.get("shipment_count")) for r in data],
			}],
		},
		"type": "bar",
		"title": _("Top Airlines by Shipments"),
	}
