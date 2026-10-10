# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""TCT Job Files Detail — drill-down for Open / Avg Age / Handled KPI cards."""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint, nowdate

from logistics.transport.tct_report_utils import (
	OPEN_EXCLUDES,
	date_bounds,
	dim_clauses,
	normalize_filters,
	vehicle_type_clause,
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
		{"fieldname": "name", "label": _("Transport Job"), "fieldtype": "Link", "options": "Transport Job", "width": 150},
		{"fieldname": "status", "label": _("Job Status"), "fieldtype": "Data", "width": 120},
		{"fieldname": "booking_date", "label": _("Booking Date"), "fieldtype": "Date", "width": 120},
		{"fieldname": "age_days", "label": _("Age (days)"), "fieldtype": "Int", "width": 100},
		{"fieldname": "vehicle_type", "label": _("Vehicle Type"), "fieldtype": "Link", "options": "Vehicle Type", "width": 140},
		{"fieldname": "transport_mode", "label": _("Transport Mode"), "fieldtype": "Link", "options": "Transport Mode", "width": 140},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 180},
		{"fieldname": "customer_ref_no", "label": _("Customer Ref No"), "fieldtype": "Data", "width": 140},
		{"fieldname": "company", "label": _("Company"), "fieldtype": "Link", "options": "Company", "width": 160},
		{"fieldname": "branch", "label": _("Branch"), "fieldtype": "Link", "options": "Branch", "width": 120},
		{"fieldname": "cost_center", "label": _("Cost Center"), "fieldtype": "Link", "options": "Cost Center", "width": 130},
		{"fieldname": "profit_center", "label": _("Profit Center"), "fieldtype": "Link", "options": "Profit Center", "width": 130},
	]


def get_data(filters):
	today = nowdate()
	from_date, to_date = date_bounds(filters)
	dim_c, dim_v = dim_clauses(filters)
	vt_c, vt_v = vehicle_type_clause(filters)
	conditions = list(dim_c) + list(vt_c)
	values = list(dim_v) + list(vt_v)

	scope = filters.scope
	if scope == "Open":
		ph = ", ".join(["%s"] * len(OPEN_EXCLUDES))
		conditions.append("status NOT IN ({0})".format(ph))
		values.extend(OPEN_EXCLUDES)
	elif scope == "Handled":
		conditions.append("booking_date BETWEEN %s AND %s")
		values.extend([from_date, to_date])
	else:
		conditions.append(
			"(status NOT IN ({0}) OR booking_date BETWEEN %s AND %s)".format(
				", ".join(["%s"] * len(OPEN_EXCLUDES))
			)
		)
		values.extend(list(OPEN_EXCLUDES) + [from_date, to_date])

	where = " AND ".join(conditions) if conditions else "1=1"
	return frappe.db.sql(
		"""
		SELECT
			name, status, booking_date, vehicle_type, transport_mode, customer,
			customer_ref_no, company, branch, cost_center, profit_center,
			GREATEST(DATEDIFF(%s, booking_date), 0) AS age_days
		FROM `tabTransport Job`
		WHERE {where}
		ORDER BY booking_date DESC, name DESC
		LIMIT 5000
		""".format(where=where),
		tuple([today] + values),
		as_dict=True,
	)


def get_summary(data, filters):
	ages = [cint(r.get("age_days")) for r in data if r.get("booking_date")]
	avg_age = round(sum(ages) / len(ages), 1) if ages else 0
	return [
		{"label": _("Rows"), "value": len(data), "datatype": "Int", "indicator": "Blue"},
		{"label": _("Avg Age (days)"), "value": avg_age, "datatype": "Float", "indicator": "Orange"},
		{"label": _("Scope"), "value": filters.scope, "datatype": "Data"},
		{"label": _("FY"), "value": filters.fiscal_year, "datatype": "Int"},
	]


def get_chart(data, filters):
	by_status = {}
	for row in data:
		key = row.get("status") or _("Unknown")
		by_status[key] = by_status.get(key, 0) + 1
	labels = list(by_status.keys())[:12]
	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Jobs"), "values": [by_status[label] for label in labels]}],
		},
		"type": "bar",
		"title": _("Transport Jobs by Status ({0})").format(filters.scope),
	}
