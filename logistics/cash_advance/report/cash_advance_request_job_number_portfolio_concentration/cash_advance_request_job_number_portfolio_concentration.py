# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt
from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint, flt

from logistics.analytics_reports.management_reports import bar_top_numeric


def execute(filters=None):
	filters = frappe._dict(filters or {})
	limit = cint(filters.get("limit")) or 15
	conditions = ["car.docstatus = 1", "IFNULL(cari.job_number, '') != ''"]
	values = {"limit": limit}

	for field in ("company", "branch", "cost_center", "profit_center", "payee"):
		if filters.get(field):
			conditions.append(f"car.`{field}` = %({field})s")
			values[field] = filters[field]

	if filters.get("job_number"):
		conditions.append("cari.job_number = %(job_number)s")
		values["job_number"] = filters["job_number"]

	where = " AND ".join(conditions)
	columns = [
		{"fieldname": "bucket", "label": _("Job Number"), "fieldtype": "Link", "options": "Job Number", "width": 220},
		{"fieldname": "metric", "label": _("Value"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "share_pct", "label": _("Of total %"), "fieldtype": "Percent", "width": 100},
	]

	rows = frappe.db.sql(
		f"""
		SELECT cari.job_number AS bucket, COALESCE(SUM(car.total_requested), 0) AS metric
		FROM `tabCash Advance Request Item` cari
		INNER JOIN `tabCash Advance Request` car ON car.name = cari.parent
		WHERE {where}
		GROUP BY cari.job_number
		ORDER BY metric DESC
		LIMIT %(limit)s
		""",
		values,
		as_dict=1,
	)

	total_metric = sum(flt(r.get("metric")) for r in rows) or 1
	for row in rows:
		row["share_pct"] = round(100.0 * flt(row.get("metric")) / total_metric, 2)

	chart = bar_top_numeric(rows, "bucket", "metric", limit=limit, dataset_label=_("Value"))
	summary = [{"label": _("Top slice total"), "value": flt(total_metric), "indicator": "green"}]
	return columns, rows, None, chart, summary
