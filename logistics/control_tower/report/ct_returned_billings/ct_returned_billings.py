# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import nowdate

from logistics.control_tower.api import resolve_org_filters, _dim_clauses


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("organization"):
		frappe.throw(_("Organization is required"))
	year = int(filters.get("fiscal_year_yyyy") or nowdate()[:4])
	org_filters = resolve_org_filters(filters.organization)

	conditions = ["returned_on BETWEEN %s AND %s"]
	values = ["{0}-01-01".format(year), "{0}-12-31".format(year)]
	dim_conditions, dim_values = _dim_clauses(org_filters)
	conditions.extend(dim_conditions)
	values.extend(dim_values)
	if filters.get("module"):
		conditions.append("module = %s")
		values.append(filters.module)

	rows = frappe.db.sql(
		"""
		SELECT name, returned_on, module, resolution_status, job_no, invoice,
		       customer, branch, cost_center, profit_center, reason, resolved_on
		FROM `tabReturned Billing`
		WHERE {where}
		ORDER BY returned_on DESC
		""".format(where=" AND ".join(conditions)),
		tuple(values),
		as_dict=True,
	)

	columns = [
		{"fieldname": "name", "label": _("Name"), "fieldtype": "Link", "options": "Returned Billing", "width": 110},
		{"fieldname": "returned_on", "label": _("Returned On"), "fieldtype": "Date", "width": 110},
		{"fieldname": "module", "label": _("Module"), "fieldtype": "Data", "width": 110},
		{"fieldname": "resolution_status", "label": _("Status"), "fieldtype": "Data", "width": 110},
		{"fieldname": "job_no", "label": _("Job"), "fieldtype": "Link", "options": "Job Number", "width": 130},
		{"fieldname": "invoice", "label": _("Invoice"), "fieldtype": "Link", "options": "Sales Invoice", "width": 140},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 200},
		{"fieldname": "branch", "label": _("Branch"), "fieldtype": "Link", "options": "Branch", "width": 110},
		{"fieldname": "cost_center", "label": _("Cost Center"), "fieldtype": "Link", "options": "Cost Center", "width": 130},
		{"fieldname": "profit_center", "label": _("Profit Center"), "fieldtype": "Link", "options": "Profit Center", "width": 130},
		{"fieldname": "reason", "label": _("Reason"), "fieldtype": "Data", "width": 200},
		{"fieldname": "resolved_on", "label": _("Resolved On"), "fieldtype": "Date", "width": 110},
	]

	by_module = {}
	for r in rows:
		by_module[r["module"]] = by_module.get(r["module"], 0) + 1
	chart = {
		"data": {
			"labels": list(by_module.keys()),
			"datasets": [{"name": _("Returned Billings"), "values": list(by_module.values())}],
		},
		"type": "bar",
		"title": _("Returned Billings by Module"),
	}
	report_summary = [
		{"label": _("Total Returned"), "value": len(rows), "datatype": "Int", "indicator": "Red"},
	]
	return columns, rows, None, chart, report_summary
