# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""TCT Vehicle Type Volumes — drill-down for the Top Vehicle Types chart."""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt

from logistics.transport.tct_report_utils import (
	date_bounds,
	dim_clauses,
	normalize_filters,
	vehicle_type_clause,
)


def execute(filters=None):
	filters = normalize_filters(filters)
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	summary = [
		{"label": _("Vehicle Types"), "value": len(data), "datatype": "Int", "indicator": "Blue"},
		{
			"label": _("Jobs"),
			"value": int(sum(flt(row.get("job_count")) for row in data)),
			"datatype": "Int",
			"indicator": "Green",
		},
		{"label": _("FY"), "value": filters.fiscal_year, "datatype": "Int"},
	]
	return columns, data, None, chart, summary


def get_columns():
	return [
		{"fieldname": "vehicle_type", "label": _("Vehicle Type"), "fieldtype": "Link", "options": "Vehicle Type", "width": 180},
		{"fieldname": "job_count", "label": _("Jobs"), "fieldtype": "Int", "width": 100},
		{"fieldname": "total_weight", "label": _("Total Weight"), "fieldtype": "Float", "width": 130},
		{"fieldname": "open_count", "label": _("Open"), "fieldtype": "Int", "width": 90},
		{"fieldname": "pct_of_total", "label": _("% of Total"), "fieldtype": "Percent", "width": 100},
	]


def get_data(filters):
	from_date, to_date = date_bounds(filters)
	dim_c, dim_v = dim_clauses(filters)
	vt_c, vt_v = vehicle_type_clause(filters)
	conditions = dim_c + vt_c + [
		"booking_date BETWEEN %s AND %s",
		"IFNULL(vehicle_type, '') != ''",
	]
	values = dim_v + vt_v + [from_date, to_date]
	where = " AND ".join(conditions)
	rows = frappe.db.sql(
		"""
		SELECT
			vehicle_type,
			COUNT(*) AS job_count,
			SUM(IFNULL(total_weight, 0)) AS total_weight,
			SUM(CASE WHEN status NOT IN ('Completed', 'Closed', 'Cancelled') THEN 1 ELSE 0 END) AS open_count
		FROM `tabTransport Job`
		WHERE {where}
		GROUP BY vehicle_type
		ORDER BY job_count DESC
		LIMIT %s
		""".format(where=where),
		tuple(values + [filters.limit]),
		as_dict=True,
	)
	total = sum(flt(row.job_count) for row in rows) or 1
	for row in rows:
		row.pct_of_total = round((flt(row.job_count) / total) * 100.0, 1)
		row.total_weight = round(flt(row.total_weight), 2)
	return rows


def get_chart(data):
	return {
		"data": {
			"labels": [row.get("vehicle_type") or "" for row in data],
			"datasets": [{
				"name": _("Jobs"),
				"values": [flt(row.get("job_count")) for row in data],
			}],
		},
		"type": "bar",
		"title": _("Top Vehicle Types by Jobs"),
	}
