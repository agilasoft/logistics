# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""AFCT Returned Billings — drill-down for Returned Billings KPI card."""

from __future__ import unicode_literals

import frappe
from frappe import _

from logistics.air_freight.afct_report_utils import dim_clauses, normalize_filters, year_bounds


def execute(filters=None):
	filters = normalize_filters(filters)
	if not frappe.db.exists("DocType", "Returned Billing"):
		return get_columns(), [], _("Returned Billing DocType is not installed.")

	columns = get_columns()
	data = get_data(filters)
	by_status = {}
	for r in data:
		key = r.get("resolution_status") or _("Unknown")
		by_status[key] = by_status.get(key, 0) + 1
	chart = {
		"data": {
			"labels": list(by_status.keys()),
			"datasets": [{"name": _("Count"), "values": list(by_status.values())}],
		},
		"type": "donut",
		"title": _("Returned Billings by Status"),
	}
	summary = [
		{"label": _("Returned"), "value": len(data), "datatype": "Int", "indicator": "Red"},
		{"label": _("FY"), "value": filters.fiscal_year, "datatype": "Int"},
	]
	return columns, data, None, chart, summary


def get_columns():
	return [
		{"fieldname": "name", "label": _("Returned Billing"), "fieldtype": "Link", "options": "Returned Billing", "width": 140},
		{"fieldname": "returned_on", "label": _("Returned On"), "fieldtype": "Date", "width": 110},
		{"fieldname": "resolution_status", "label": _("Status"), "fieldtype": "Data", "width": 110},
		{"fieldname": "module", "label": _("Module"), "fieldtype": "Data", "width": 110},
		{"fieldname": "job_no", "label": _("Job"), "fieldtype": "Data", "width": 140},
		{"fieldname": "invoice", "label": _("Invoice"), "fieldtype": "Link", "options": "Sales Invoice", "width": 140},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 180},
		{"fieldname": "company", "label": _("Company"), "fieldtype": "Link", "options": "Company", "width": 150},
		{"fieldname": "branch", "label": _("Branch"), "fieldtype": "Link", "options": "Branch", "width": 120},
		{"fieldname": "cost_center", "label": _("Cost Center"), "fieldtype": "Link", "options": "Cost Center", "width": 130},
		{"fieldname": "profit_center", "label": _("Profit Center"), "fieldtype": "Link", "options": "Profit Center", "width": 130},
		{"fieldname": "reason", "label": _("Reason"), "fieldtype": "Data", "width": 200},
		{"fieldname": "resolved_on", "label": _("Resolved On"), "fieldtype": "Date", "width": 110},
	]


def get_data(filters):
	from_date, to_date = date_bounds(filters)
	dim_c, dim_v = dim_clauses(filters)
	conditions = dim_c + ["returned_on BETWEEN %s AND %s"]
	values = dim_v + [from_date, to_date]

	if frappe.db.has_column("Returned Billing", "module"):
		conditions.append("(module = %s OR IFNULL(module, '') = '')")
		values.append("Air Freight")

	unloco = filters.get("unloco")
	if unloco:
		conditions.append(
			"""(
				IFNULL(job_no, '') != ''
				AND EXISTS (
					SELECT 1 FROM `tabAir Shipment` s
					WHERE s.name = `tabReturned Billing`.job_no
					  AND (s.origin_port = %s OR s.destination_port = %s)
				)
			)"""
		)
		values.extend([unloco, unloco])

	return frappe.db.sql(
		"""
		SELECT
			name, returned_on, resolution_status, module, job_no, invoice,
			customer, company, branch, cost_center, profit_center, reason, resolved_on
		FROM `tabReturned Billing`
		WHERE {where}
		ORDER BY returned_on DESC
		LIMIT 5000
		""".format(where=" AND ".join(conditions) or "1=1"),
		tuple(values),
		as_dict=True,
	)
