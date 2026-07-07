# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt
from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint, flt

from logistics.cash_advance.totals_sync import unliquidated_join_sql, unliquidated_sql_expr


def execute(filters=None):
	filters = frappe._dict(filters or {})
	car = "car"
	unliquidated_expr = unliquidated_sql_expr(car)
	joins = unliquidated_join_sql(car)

	where, values = ["car.docstatus = 1", "car.liquidation_due_date IS NOT NULL", f"({unliquidated_expr}) > 0"], {}
	for field in ("company", "branch", "cost_center", "profit_center", "payee"):
		if filters.get(field):
			where.append(f"car.`{field}` = %({field})s")
			values[field] = filters[field]
	if filters.get("job_number"):
		where.append(
			"""EXISTS (
				SELECT 1 FROM `tabCash Advance Request Item` cari
				WHERE cari.parent = car.name AND cari.job_number = %(job_number)s
			)"""
		)
		values["job_number"] = filters["job_number"]

	columns = [
		{"fieldname": "age_bucket", "label": _("Aging bucket"), "fieldtype": "Data", "width": 180},
		{"fieldname": "documents", "label": _("Documents"), "fieldtype": "Int", "width": 120},
		{"fieldname": "amount", "label": _("Unliquidated"), "fieldtype": "Currency", "width": 160},
	]

	data = frappe.db.sql(
		f"""
		SELECT CASE
			WHEN DATEDIFF(CURDATE(), DATE(car.liquidation_due_date)) > 90 THEN '90+ days overdue'
			WHEN DATEDIFF(CURDATE(), DATE(car.liquidation_due_date)) > 60 THEN '61-90 days overdue'
			WHEN DATEDIFF(CURDATE(), DATE(car.liquidation_due_date)) > 30 THEN '31-60 days overdue'
			WHEN DATEDIFF(CURDATE(), DATE(car.liquidation_due_date)) >= 1 THEN '1-30 days overdue'
			WHEN DATEDIFF(CURDATE(), DATE(car.liquidation_due_date)) = 0 THEN 'Due today'
			ELSE 'Not yet due'
		END AS age_bucket,
		COUNT(*) AS documents,
		COALESCE(SUM({unliquidated_expr}), 0) AS amount
		FROM `tabCash Advance Request` car
		{joins}
		WHERE {" AND ".join(where)}
		GROUP BY age_bucket
		ORDER BY FIELD(age_bucket,
			'90+ days overdue',
			'61-90 days overdue',
			'31-60 days overdue',
			'1-30 days overdue',
			'Due today',
			'Not yet due'
		)
		""",
		values,
		as_dict=True,
	)

	total_docs = sum(cint(row.documents) for row in data)
	total_amount = sum(flt(row.amount) for row in data)
	summary = [
		{"label": _("Documents"), "value": total_docs, "indicator": "blue"},
		{"label": _("Unliquidated"), "value": total_amount, "indicator": "blue"},
	]
	return columns, data, None, None, summary
