# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""CCT Authority Volumes — drill-down for the Top Customs Authorities chart."""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt

from logistics.customs.cct_report_utils import (
	date_bounds,
	dim_clauses,
	normalize_filters,
	unloco_clause,
)


def execute(filters=None):
	filters = normalize_filters(filters)
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	summary = [
		{"label": _("Authorities"), "value": len(data), "datatype": "Int", "indicator": "Blue"},
		{
			"label": _("Declarations"),
			"value": int(sum(flt(row.get("declaration_count")) for row in data)),
			"datatype": "Int",
			"indicator": "Green",
		},
		{"label": _("FY"), "value": filters.fiscal_year, "datatype": "Int"},
	]
	return columns, data, None, chart, summary


def get_columns():
	return [
		{"fieldname": "customs_authority", "label": _("Customs Authority"), "fieldtype": "Link", "options": "Customs Authority", "width": 180},
		{"fieldname": "declaration_count", "label": _("Declarations"), "fieldtype": "Int", "width": 120},
		{"fieldname": "total_value", "label": _("Total Value"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "open_count", "label": _("Open"), "fieldtype": "Int", "width": 90},
		{"fieldname": "pct_of_total", "label": _("% of Total"), "fieldtype": "Percent", "width": 100},
	]


def get_data(filters):
	from_date, to_date = date_bounds(filters)
	dim_c, dim_v = dim_clauses(filters)
	unloco_c, unloco_v = unloco_clause(filters)
	conditions = dim_c + unloco_c + [
		"declaration_date BETWEEN %s AND %s",
		"IFNULL(customs_authority, '') != ''",
	]
	values = dim_v + unloco_v + [from_date, to_date]
	if filters.customs_authority:
		conditions.append("customs_authority = %s")
		values.append(filters.customs_authority)

	where = " AND ".join(conditions)
	rows = frappe.db.sql(
		"""
		SELECT
			customs_authority,
			COUNT(*) AS declaration_count,
			SUM(IFNULL(declaration_value, 0)) AS total_value,
			SUM(CASE WHEN job_status NOT IN ('Completed', 'Closed', 'Cancelled') THEN 1 ELSE 0 END) AS open_count
		FROM `tabDeclaration`
		WHERE {where}
		GROUP BY customs_authority
		ORDER BY declaration_count DESC
		LIMIT %s
		""".format(where=where),
		tuple(values + [filters.limit]),
		as_dict=True,
	)
	total = sum(flt(row.declaration_count) for row in rows) or 1
	for row in rows:
		row.pct_of_total = round((flt(row.declaration_count) / total) * 100.0, 1)
		row.total_value = round(flt(row.total_value), 2)
	return rows


def get_chart(data):
	return {
		"data": {
			"labels": [row.get("customs_authority") or "" for row in data],
			"datasets": [{
				"name": _("Declarations"),
				"values": [flt(row.get("declaration_count")) for row in data],
			}],
		},
		"type": "bar",
		"title": _("Top Customs Authorities by Declarations"),
	}
