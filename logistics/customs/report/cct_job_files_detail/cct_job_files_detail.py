# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""CCT Job Files Detail — drill-down for Open / Avg Age / Handled KPI cards."""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint, nowdate

from logistics.customs.cct_report_utils import (
	OPEN_EXCLUDES,
	date_bounds,
	dim_clauses,
	normalize_filters,
	unloco_clause,
)


def execute(filters=None):
	filters = normalize_filters(filters)
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data, filters)
	summary = get_summary(data, filters)
	return columns, data, None, chart, summary


def get_columns():
	return [
		{"fieldname": "name", "label": _("Declaration"), "fieldtype": "Link", "options": "Declaration", "width": 150},
		{"fieldname": "job_status", "label": _("Job Status"), "fieldtype": "Data", "width": 120},
		{"fieldname": "declaration_date", "label": _("Declaration Date"), "fieldtype": "Date", "width": 130},
		{"fieldname": "age_days", "label": _("Age (days)"), "fieldtype": "Int", "width": 100},
		{"fieldname": "customs_authority", "label": _("Customs Authority"), "fieldtype": "Link", "options": "Customs Authority", "width": 160},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 180},
		{"fieldname": "port_of_loading", "label": _("Port of Loading"), "fieldtype": "Link", "options": "UNLOCO", "width": 120},
		{"fieldname": "port_of_discharge", "label": _("Port of Discharge"), "fieldtype": "Link", "options": "UNLOCO", "width": 130},
		{"fieldname": "declaration_type", "label": _("Declaration Type"), "fieldtype": "Data", "width": 130},
		{"fieldname": "declaration_number", "label": _("Declaration Number"), "fieldtype": "Data", "width": 150},
		{"fieldname": "company", "label": _("Company"), "fieldtype": "Link", "options": "Company", "width": 160},
		{"fieldname": "branch", "label": _("Branch"), "fieldtype": "Link", "options": "Branch", "width": 120},
		{"fieldname": "cost_center", "label": _("Cost Center"), "fieldtype": "Link", "options": "Cost Center", "width": 130},
		{"fieldname": "profit_center", "label": _("Profit Center"), "fieldtype": "Link", "options": "Profit Center", "width": 130},
	]


def get_data(filters):
	today = nowdate()
	from_date, to_date = date_bounds(filters)
	dim_c, dim_v = dim_clauses(filters)
	unloco_c, unloco_v = unloco_clause(filters)
	conditions = list(dim_c) + list(unloco_c)
	values = list(dim_v) + list(unloco_v)

	scope = filters.scope
	if scope == "Open":
		ph = ", ".join(["%s"] * len(OPEN_EXCLUDES))
		conditions.append("job_status NOT IN ({0})".format(ph))
		values.extend(OPEN_EXCLUDES)
	elif scope == "Handled":
		conditions.append("declaration_date BETWEEN %s AND %s")
		values.extend([from_date, to_date])
	else:
		conditions.append(
			"(job_status NOT IN ({0}) OR declaration_date BETWEEN %s AND %s)".format(
				", ".join(["%s"] * len(OPEN_EXCLUDES))
			)
		)
		values.extend(list(OPEN_EXCLUDES) + [from_date, to_date])

	where = " AND ".join(conditions) if conditions else "1=1"
	return frappe.db.sql(
		"""
		SELECT
			name, job_status, declaration_date, customs_authority, customer,
			port_of_loading, port_of_discharge, declaration_type, declaration_number,
			company, branch, cost_center, profit_center,
			GREATEST(DATEDIFF(%s, declaration_date), 0) AS age_days
		FROM `tabDeclaration`
		WHERE {where}
		ORDER BY declaration_date DESC, name DESC
		LIMIT 5000
		""".format(where=where),
		tuple([today] + values),
		as_dict=True,
	)


def get_summary(data, filters):
	ages = [cint(r.get("age_days")) for r in data if r.get("declaration_date")]
	avg_age = round(sum(ages) / len(ages), 1) if ages else 0
	return [
		{"label": _("Rows"), "value": len(data), "datatype": "Int", "indicator": "Blue"},
		{"label": _("Avg Age (days)"), "value": avg_age, "datatype": "Float", "indicator": "Orange"},
		{"label": _("Scope"), "value": filters.scope, "datatype": "Data"},
		{"label": _("FY"), "value": filters.fiscal_year, "datatype": "Int"},
	]


def get_chart(data, filters):
	by_status = {}
	for r in data:
		key = r.get("job_status") or _("Unknown")
		by_status[key] = by_status.get(key, 0) + 1
	labels = list(by_status.keys())[:12]
	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Declarations"), "values": [by_status[label] for label in labels]}],
		},
		"type": "bar",
		"title": _("Declarations by Status ({0})").format(filters.scope),
	}
