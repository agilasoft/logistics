# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt
"""Cash Advance Liquidation Aging.

Line-level aging of unliquidated Cash Advance Requests against their
``liquidation_due_date``. Used for collections, follow-up and provisioning.
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

AGING_BUCKETS = (
	"90+ days overdue",
	"61-90 days overdue",
	"31-60 days overdue",
	"1-30 days overdue",
	"Due today",
	"Not yet due",
	"No due date",
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	as_on = getdate(filters.get("as_on_date") or nowdate())

	columns = _columns()
	rows = _rows(filters, as_on)
	chart, summary = _chart_and_summary(rows)
	return columns, rows, None, chart, summary


def _columns():
	return [
		{"fieldname": "name", "label": _("Request"), "fieldtype": "Link", "options": "Cash Advance Request", "width": 130},
		{"fieldname": "date", "label": _("Request Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "release_date", "label": _("Release Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "liquidation_due_date", "label": _("Liquidation Due"), "fieldtype": "Date", "width": 110},
		{"fieldname": "days_overdue", "label": _("Days Overdue"), "fieldtype": "Int", "width": 100},
		{"fieldname": "age_bucket", "label": _("Aging Bucket"), "fieldtype": "Data", "width": 140},
		{"fieldname": "payee", "label": _("Payee"), "fieldtype": "Link", "options": "Supplier", "width": 140},
		{"fieldname": "payee_name", "label": _("Payee Name"), "fieldtype": "Data", "width": 160},
		{"fieldname": "job_number", "label": _("Job Number"), "fieldtype": "Link", "options": "Job Number", "width": 120},
		{"fieldname": "company", "label": _("Company"), "fieldtype": "Link", "options": "Company", "width": 130},
		{"fieldname": "branch", "label": _("Branch"), "fieldtype": "Link", "options": "Branch", "width": 110},
		{"fieldname": "cost_center", "label": _("Cost Center"), "fieldtype": "Link", "options": "Cost Center", "width": 130},
		{"fieldname": "profit_center", "label": _("Profit Center"), "fieldtype": "Link", "options": "Profit Center", "width": 130},
		{"fieldname": "total_requested", "label": _("Total Requested"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "total_liquidated", "label": _("Total Liquidated"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "unliquidated", "label": _("Unliquidated"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "refunded", "label": _("Refunded"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "returned", "label": _("Returned"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "status_label", "label": _("Status"), "fieldtype": "Data", "width": 90},
	]


def _rows(filters, as_on):
	unliquidated_expr = (
		"IFNULL(car.total_requested, 0) - IFNULL(liq.total_liquidated, 0) "
		"- IFNULL(ack.returned, 0) + IFNULL(ack.refunded, 0)"
	)
	conditions = ["({0}) > 0".format(unliquidated_expr)]
	values = {"as_on": as_on}

	if cint(filters.get("include_drafts")):
		conditions.append("car.docstatus < 2")
	else:
		conditions.append("car.docstatus = 1")

	for field in ("company", "branch", "cost_center", "profit_center", "job_number", "payee"):
		if filters.get(field):
			conditions.append("car.`{0}` = %({0})s".format(field))
			values[field] = filters[field]

	where = " AND ".join(conditions)

	data = frappe.db.sql(
		"""
		SELECT
			car.name, car.date, car.release_date, car.liquidation_due_date,
			car.payee, car.payee_name, car.job_number,
			car.company, car.branch, car.cost_center, car.profit_center,
			car.total_requested,
			IFNULL(liq.total_liquidated, 0) AS total_liquidated,
			{unliquidated_expr} AS unliquidated,
			IFNULL(ack.refunded, 0) AS refunded,
			IFNULL(ack.returned, 0) AS returned,
			car.docstatus,
			CASE
				WHEN car.liquidation_due_date IS NULL THEN NULL
				ELSE DATEDIFF(%(as_on)s, car.liquidation_due_date)
			END AS days_overdue
		FROM `tabCash Advance Request` car
		LEFT JOIN (
			SELECT
				cash_advance_request,
				SUM(total_liquidated) AS total_liquidated
			FROM `tabCash Advance Liquidation`
			WHERE docstatus = 1
			GROUP BY cash_advance_request
		) liq ON liq.cash_advance_request = car.name
		LEFT JOIN (
			SELECT
				cash_advance_request,
				SUM(CASE WHEN acknowledgment_type = 'Receipt' THEN amount ELSE 0 END) AS returned,
				SUM(CASE WHEN acknowledgment_type = 'Payment' THEN amount ELSE 0 END) AS refunded
			FROM `tabCash Acknowledgment`
			WHERE docstatus = 1
			GROUP BY cash_advance_request
		) ack ON ack.cash_advance_request = car.name
		WHERE {where}
		ORDER BY days_overdue DESC, car.liquidation_due_date ASC
		""".format(where=where, unliquidated_expr=unliquidated_expr),
		values,
		as_dict=1,
	)

	rows = []
	bucket_filter = (filters.get("aging_bucket") or "").strip()
	only_overdue = cint(filters.get("only_overdue"))
	for r in data:
		r["age_bucket"] = _bucket_for(r.get("days_overdue"))
		r["status_label"] = _("Draft") if cint(r.get("docstatus")) == 0 else _("Submitted")
		if bucket_filter and r["age_bucket"] != bucket_filter:
			continue
		if only_overdue and r["age_bucket"] in ("Not yet due", "Due today", "No due date"):
			continue
		rows.append(r)
	return rows


def _bucket_for(days_overdue):
	if days_overdue is None:
		return "No due date"
	d = cint(days_overdue)
	if d > 90:
		return "90+ days overdue"
	if d > 60:
		return "61-90 days overdue"
	if d > 30:
		return "31-60 days overdue"
	if d >= 1:
		return "1-30 days overdue"
	if d == 0:
		return "Due today"
	return "Not yet due"


def _chart_and_summary(rows):
	totals = {b: {"documents": 0, "amount": 0.0} for b in AGING_BUCKETS}
	for r in rows:
		bucket = r.get("age_bucket") or "No due date"
		bucket_totals = totals.setdefault(bucket, {"documents": 0, "amount": 0.0})
		bucket_totals["documents"] += 1
		bucket_totals["amount"] += flt(r.get("unliquidated"))

	labels = list(AGING_BUCKETS)
	values = [round(totals[b]["amount"], 2) for b in labels]
	chart = {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Unliquidated"), "values": values}],
		},
		"type": "bar",
		"colors": ["#e74c3c", "#e67e22", "#f1c40f", "#f39c12", "#3498db", "#2ecc71", "#95a5a6"],
	}

	overdue_amount = sum(totals[b]["amount"] for b in AGING_BUCKETS if b.endswith("overdue"))
	overdue_count = sum(totals[b]["documents"] for b in AGING_BUCKETS if b.endswith("overdue"))
	total_outstanding = sum(flt(r.get("unliquidated")) for r in rows)

	summary = [
		{"label": _("Outstanding requests"), "value": len(rows), "indicator": "blue"},
		{"label": _("Total unliquidated"), "value": flt(total_outstanding), "indicator": "blue"},
		{
			"label": _("Overdue requests"),
			"value": overdue_count,
			"indicator": "red" if overdue_count else "green",
		},
		{
			"label": _("Overdue unliquidated"),
			"value": flt(overdue_amount),
			"indicator": "red" if overdue_amount else "green",
		},
	]
	return chart, summary
