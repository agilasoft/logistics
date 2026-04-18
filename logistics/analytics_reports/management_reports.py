# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt
"""Management and KPI-oriented script report drivers (beyond simple counts)."""

from __future__ import unicode_literals

import json
import re

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from logistics.analytics_reports.bootstrap import (
	_chart_from_rows,
	bar_top_numeric,
	series_chart,
)


def _table(doctype):
	return "`tab{0}`".format(doctype.replace("`", ""))


def _valid_field(fieldname):
	return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", fieldname or ""))


def _pick_amount_field(ref_doctype):
	for fname in (
		"grand_total",
		"base_grand_total",
		"total_amount",
		"total",
		"declaration_value",
		"net_amount",
		"total_receivable",
		"total_payable",
		"chargeable",
		"estimated_penalty_amount",
	):
		if frappe.db.has_column(ref_doctype, fname):
			return fname
	return None


def _base_where(ref_doctype, filters, include_cancelled=False):
	conditions = ["1=1"]
	values = {}
	if filters.get("from_date"):
		conditions.append("creation >= %(from_date)s")
		values["from_date"] = getdate(filters["from_date"])
	if filters.get("to_date"):
		conditions.append("creation <= %(to_date)s")
		values["to_date"] = getdate(filters["to_date"])
	if filters.get("company") and frappe.db.has_column(ref_doctype, "company"):
		conditions.append("company = %(company)s")
		values["company"] = filters["company"]
	if frappe.db.has_column(ref_doctype, "docstatus") and not include_cancelled:
		conditions.append("docstatus < 2")
	return " AND ".join(conditions), values


def _empty(message):
	columns = [{"fieldname": "message", "label": _("Message"), "fieldtype": "Data", "width": 400}]
	data = [{"message": message}]
	chart = _chart_from_rows([{"bucket": _("N/A"), "v": 0}], "v", "bucket")
	return columns, data, None, chart, []


def kpi_executive_snapshot(ref, filters, options):
	"""Draft vs submitted vs cancelled, totals, and booked value where a currency column exists."""
	if not frappe.db.exists("DocType", ref):
		return _empty(_("DocType not found: {0}").format(ref))
	table = _table(ref)
	where, values = _base_where(ref, filters, include_cancelled=True)
	amt = _pick_amount_field(ref)
	amt_sql = "COALESCE(SUM(`{0}`), 0)".format(amt) if amt else "0"
	columns = [
		{"fieldname": "drafts", "label": _("Draft documents"), "fieldtype": "Int", "width": 120},
		{"fieldname": "submitted", "label": _("Submitted"), "fieldtype": "Int", "width": 100},
		{"fieldname": "cancelled", "label": _("Cancelled"), "fieldtype": "Int", "width": 100},
		{"fieldname": "in_scope", "label": _("In scope total"), "fieldtype": "Int", "width": 120},
		{"fieldname": "booked_value", "label": _("Booked value in scope"), "fieldtype": "Currency", "width": 160},
	]
	try:
		row = frappe.db.sql(
			"""
			SELECT
				SUM(CASE WHEN docstatus = 0 THEN 1 ELSE 0 END) AS drafts,
				SUM(CASE WHEN docstatus = 1 THEN 1 ELSE 0 END) AS submitted,
				SUM(CASE WHEN docstatus = 2 THEN 1 ELSE 0 END) AS cancelled,
				COUNT(*) AS in_scope,
				{amt_sql} AS booked_value
			FROM {tbl}
			WHERE {where}
			""".format(
				tbl=table,
				where=where,
				amt_sql=amt_sql,
			),
			values,
			as_dict=1,
		)[0]
	except Exception:
		frappe.log_error(frappe.get_traceback(), "kpi_executive_snapshot:{0}".format(ref))
		return _empty(_("Could not load executive snapshot."))
	data = [row]
	chart = bar_top_numeric(
		[
			{"k": _("Drafts"), "v": cint(row.get("drafts"))},
			{"k": _("Submitted"), "v": cint(row.get("submitted"))},
			{"k": _("Cancelled"), "v": cint(row.get("cancelled"))},
		],
		"k",
		"v",
		dataset_label=_("Documents"),
	)
	summary = [
		{"label": _("In scope"), "value": cint(row.get("in_scope")), "indicator": "blue"},
		{"label": _("Booked value"), "value": flt(row.get("booked_value")), "indicator": "green"},
	]
	return columns, data, None, chart, summary


def kpi_trend_volume_value(ref, filters, options):
	"""Weekly or monthly buckets: document count and summed value field."""
	if not frappe.db.exists("DocType", ref):
		return _empty(_("DocType not found: {0}").format(ref))
	grain = options.get("grain") or "week"
	table = _table(ref)
	where, values = _base_where(ref, filters)
	if grain == "month":
		bucket_expr = "DATE_FORMAT(creation, '%%Y-%%m')"
		bucket_label = _("Month")
	elif grain == "week":
		bucket_expr = "YEARWEEK(creation, 3)"
		bucket_label = _("Week")
	else:
		bucket_expr = "DATE(creation)"
		bucket_label = _("Day")
	amt = options.get("amount_field") or _pick_amount_field(ref)
	amt_sql = "COALESCE(SUM(`{0}`), 0)".format(amt) if amt else "0"
	columns = [
		{"fieldname": "period", "label": bucket_label, "fieldtype": "Data", "width": 120},
		{"fieldname": "documents", "label": _("Documents"), "fieldtype": "Int", "width": 100},
		{"fieldname": "value_total", "label": _("Value total"), "fieldtype": "Currency", "width": 140},
	]
	try:
		data = frappe.db.sql(
			"""
			SELECT {bucket} AS period,
				COUNT(*) AS documents,
				{amt_sql} AS value_total
			FROM {tbl}
			WHERE {where}
			GROUP BY {bucket}
			ORDER BY period DESC
			LIMIT 52
			""".format(
				bucket=bucket_expr,
				tbl=table,
				where=where,
				amt_sql=amt_sql,
			),
			values,
			as_dict=1,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "kpi_trend_volume_value:{0}".format(ref))
		return _empty(_("Could not load trend data."))
	if not data:
		data = [{"period": _("No data"), "documents": 0, "value_total": 0}]
	chart = series_chart(data, "period", "value_total", chart_type="line")
	summary = [
		{"label": _("Documents in view"), "value": sum(cint(r.get("documents")) for r in data), "indicator": "blue"},
		{"label": _("Value in view"), "value": sum(flt(r.get("value_total")) for r in data), "indicator": "green"},
	]
	return columns, data, None, chart, summary


def kpi_pipeline_mix(ref, filters, options):
	"""Status (or other) dimension with count and share of total."""
	field = options.get("field") or "status"
	if not _valid_field(field) or not frappe.db.has_column(ref, field):
		return _empty(_("Field not available on {0}: {1}").format(ref, field))
	table = _table(ref)
	where, values = _base_where(ref, filters)
	columns = [
		{"fieldname": "bucket", "label": _(field.replace("_", " ").title()), "fieldtype": "Data", "width": 200},
		{"fieldname": "documents", "label": _("Documents"), "fieldtype": "Int", "width": 100},
		{"fieldname": "share_pct", "label": _("Share %"), "fieldtype": "Percent", "width": 100},
	]
	try:
		rows = frappe.db.sql(
			"""
			SELECT COALESCE(CAST(`{field}` AS CHAR), '') AS bucket, COUNT(*) AS documents
			FROM {tbl}
			WHERE {where}
			GROUP BY COALESCE(CAST(`{field}` AS CHAR), '')
			ORDER BY documents DESC
			LIMIT 40
			""".format(
				field=field,
				tbl=table,
				where=where,
			),
			values,
			as_dict=1,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "kpi_pipeline_mix:{0}".format(ref))
		return _empty(_("Could not load pipeline mix."))
	total = sum(cint(r.get("documents")) for r in rows) or 1
	for r in rows:
		r["share_pct"] = round(100.0 * cint(r.get("documents")) / total, 2)
	chart = series_chart(rows, "bucket", "share_pct", chart_type="bar")
	summary = [{"label": _("Total classified"), "value": total, "indicator": "blue"}]
	return columns, rows, None, chart, summary


def kpi_top_value_concentration(ref, filters, options):
	"""Top N group values by summed amount (or count if no amount column)."""
	field = options.get("field") or "customer"
	if not _valid_field(field) or not frappe.db.has_column(ref, field):
		return _empty(_("Field not available on {0}: {1}").format(ref, field))
	limit = cint(options.get("limit")) or 12
	table = _table(ref)
	where, values = _base_where(ref, filters)
	amt = _pick_amount_field(ref)
	if amt:
		val_sql = "COALESCE(SUM(`{0}`), 0)".format(amt)
		val_label = _("Value")
	else:
		val_sql = "COUNT(*)"
		val_label = _("Documents")
	columns = [
		{"fieldname": "bucket", "label": _(field.replace("_", " ").title()), "fieldtype": "Data", "width": 220},
		{"fieldname": "metric", "label": val_label, "fieldtype": "Currency" if amt else "Int", "width": 140},
		{"fieldname": "share_pct", "label": _("Of total %"), "fieldtype": "Percent", "width": 100},
	]
	try:
		rows = frappe.db.sql(
			"""
			SELECT COALESCE(CAST(`{field}` AS CHAR), '') AS bucket, {val_sql} AS metric
			FROM {tbl}
			WHERE {where}
			GROUP BY COALESCE(CAST(`{field}` AS CHAR), '')
			ORDER BY metric DESC
			LIMIT {limit}
			""".format(
				field=field,
				val_sql=val_sql,
				tbl=table,
				where=where,
				limit=limit,
			),
			values,
			as_dict=1,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "kpi_top_value_concentration:{0}".format(ref))
		return _empty(_("Could not load concentration view."))
	total_metric = sum(flt(r.get("metric")) for r in rows) or 1
	for r in rows:
		r["share_pct"] = round(100.0 * flt(r.get("metric")) / total_metric, 2)
	chart = bar_top_numeric(rows, "bucket", "metric", limit=limit, dataset_label=val_label)
	summary = [{"label": _("Top slice total"), "value": flt(total_metric), "indicator": "green"}]
	return columns, rows, None, chart, summary


def kpi_aging_open_backlog(ref, filters, options):
	"""Age buckets for draft (docstatus 0) documents still open."""
	if not frappe.db.has_column(ref, "docstatus"):
		return _empty(_("Aging backlog needs docstatus on {0}").format(ref))
	table = _table(ref)
	where, values = _base_where(ref, filters, include_cancelled=True)
	where = where + " AND docstatus = 0"
	columns = [
		{"fieldname": "age_bucket", "label": _("Age bucket"), "fieldtype": "Data", "width": 160},
		{"fieldname": "documents", "label": _("Open drafts"), "fieldtype": "Int", "width": 120},
	]
	try:
		data = frappe.db.sql(
			"""
			SELECT CASE
				WHEN DATEDIFF(CURDATE(), DATE(creation)) <= 7 THEN '0-7 days'
				WHEN DATEDIFF(CURDATE(), DATE(creation)) <= 30 THEN '8-30 days'
				WHEN DATEDIFF(CURDATE(), DATE(creation)) <= 90 THEN '31-90 days'
				ELSE '90+ days'
			END AS age_bucket,
			COUNT(*) AS documents
			FROM {tbl}
			WHERE {where}
			GROUP BY age_bucket
			ORDER BY FIELD(age_bucket, '0-7 days', '8-30 days', '31-90 days', '90+ days')
			""".format(
				tbl=table,
				where=where,
			),
			values,
			as_dict=1,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "kpi_aging_open_backlog:{0}".format(ref))
		return _empty(_("Could not load aging backlog."))
	if not data:
		data = [{"age_bucket": _("None"), "documents": 0}]
	chart = series_chart(data, "age_bucket", "documents", chart_type="bar")
	summary = [
		{
			"label": _("Open drafts"),
			"value": sum(cint(r.get("documents")) for r in data),
			"indicator": "orange",
		}
	]
	return columns, data, None, chart, summary


def kpi_owner_workload(ref, filters, options):
	"""Throughput and optional value by record owner (capacity view)."""
	if not frappe.db.has_column(ref, "owner"):
		return _empty(_("Owner column not on {0}").format(ref))
	table = _table(ref)
	where, values = _base_where(ref, filters)
	amt = _pick_amount_field(ref)
	amt_sql = "COALESCE(SUM(`{0}`), 0)".format(amt) if amt else "0"
	columns = [
		{"fieldname": "owner", "label": _("Owner"), "fieldtype": "Data", "width": 160},
		{"fieldname": "documents", "label": _("Documents"), "fieldtype": "Int", "width": 100},
		{"fieldname": "value_total", "label": _("Value total"), "fieldtype": "Currency", "width": 140},
	]
	try:
		data = frappe.db.sql(
			"""
			SELECT owner, COUNT(*) AS documents, {amt_sql} AS value_total
			FROM {tbl}
			WHERE {where}
			GROUP BY owner
			ORDER BY documents DESC
			LIMIT 30
			""".format(
				tbl=table,
				where=where,
				amt_sql=amt_sql if amt else "0",
			),
			values,
			as_dict=1,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "kpi_owner_workload:{0}".format(ref))
		return _empty(_("Could not load owner workload."))
	if not data:
		data = [{"owner": _("No data"), "documents": 0, "value_total": 0}]
	chart = bar_top_numeric(data, "owner", "documents", limit=15, dataset_label=_("Documents"))
	summary = [{"label": _("Active owners"), "value": len(data), "indicator": "blue"}]
	return columns, data, None, chart, summary


def kpi_branch_profit_view(ref, filters, options):
	"""Branch and profit center where present: counts and value."""
	if not frappe.db.has_column(ref, "branch"):
		return _empty(_("Branch not on {0}").format(ref))
	table = _table(ref)
	where, values = _base_where(ref, filters)
	amt = _pick_amount_field(ref)
	amt_sql = "COALESCE(SUM(`{0}`), 0)".format(amt) if amt else "0"
	has_pc = frappe.db.has_column(ref, "profit_center")
	columns = [
		{"fieldname": "branch", "label": _("Branch"), "fieldtype": "Link", "options": "Branch", "width": 140},
	]
	if has_pc:
		columns.append(
			{
				"fieldname": "profit_center",
				"label": _("Profit center"),
				"fieldtype": "Link",
				"options": "Profit Center",
				"width": 160,
			}
		)
	columns.extend(
		[
			{"fieldname": "documents", "label": _("Documents"), "fieldtype": "Int", "width": 100},
			{"fieldname": "value_total", "label": _("Value total"), "fieldtype": "Currency", "width": 140},
		]
	)
	try:
		if has_pc:
			data = frappe.db.sql(
				"""
				SELECT branch,
					COALESCE(CAST(`profit_center` AS CHAR), '') AS profit_center,
					COUNT(*) AS documents,
					{amt_sql} AS value_total
				FROM {tbl}
				WHERE {where}
				GROUP BY branch, profit_center
				ORDER BY value_total DESC
				LIMIT 40
				""".format(
					tbl=table,
					where=where,
					amt_sql=amt_sql,
				),
				values,
				as_dict=1,
			)
		else:
			data = frappe.db.sql(
				"""
				SELECT branch, COUNT(*) AS documents, {amt_sql} AS value_total
				FROM {tbl}
				WHERE {where}
				GROUP BY branch
				ORDER BY value_total DESC
				LIMIT 40
				""".format(
					tbl=table,
					where=where,
					amt_sql=amt_sql,
				),
				values,
				as_dict=1,
			)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "kpi_branch_profit_view:{0}".format(ref))
		return _empty(_("Could not load branch view."))
	if not data:
		data = [{"branch": _("None"), "documents": 0, "value_total": 0}]
	chart = bar_top_numeric(data, "branch", "value_total" if amt else "documents", limit=12)
	summary = [{"label": _("Rows"), "value": len(data), "indicator": "blue"}]
	return columns, data, None, chart, summary


def kpi_doc_health_ratio(ref, filters, options):
	"""Submitted share of all in-scope documents (quality of pipeline closure)."""
	if not frappe.db.has_column(ref, "docstatus"):
		return _empty(_("Docstatus not on {0}").format(ref))
	table = _table(ref)
	where, values = _base_where(ref, filters, include_cancelled=True)
	columns = [
		{"fieldname": "metric", "label": _("Metric"), "fieldtype": "Data", "width": 200},
		{"fieldname": "value", "label": _("Value"), "fieldtype": "Float", "width": 120},
	]
	try:
		row = frappe.db.sql(
			"""
			SELECT
				SUM(CASE WHEN docstatus = 1 THEN 1 ELSE 0 END) AS submitted,
				SUM(CASE WHEN docstatus IN (0, 1) THEN 1 ELSE 0 END) AS openish
			FROM {tbl}
			WHERE {where}
			""".format(
				tbl=table,
				where=where,
			),
			values,
			as_dict=1,
		)[0]
	except Exception:
		return _empty(_("Could not load doc health."))
	sub = cint(row.get("submitted"))
	op = cint(row.get("openish")) or 1
	ratio = round(100.0 * sub / op, 2)
	data = [
		{"metric": _("Submitted share of active pipeline %"), "value": ratio},
		{"metric": _("Submitted documents"), "value": sub},
		{"metric": _("Draft plus submitted"), "value": op},
	]
	chart = series_chart(data, "metric", "value", chart_type="bar")
	summary = [{"label": _("Submitted %"), "value": "{0}%".format(ratio), "indicator": "green" if ratio >= 70 else "orange"}]
	return columns, data, None, chart, summary


def kpi_overdue_pressure(ref, filters, options):
	"""Open drafts with due dates: severity buckets for clearance planning."""
	if not frappe.db.has_column(ref, "docstatus"):
		return _empty(_("Docstatus required on {0}").format(ref))
	due = options.get("due_field")
	if not due:
		for cand in ("due_date", "planned_date", "required_by", "expected_clearance_date", "eta"):
			if frappe.db.has_column(ref, cand):
				due = cand
				break
	if not due or not _valid_field(due):
		return _empty(_("No due date field on {0}").format(ref))
	table = _table(ref)
	where, values = _base_where(ref, filters, include_cancelled=True)
	where = where + " AND docstatus = 0"
	df = "`{0}`".format(due)
	columns = [
		{"fieldname": "severity", "label": _("Severity"), "fieldtype": "Data", "width": 200},
		{"fieldname": "documents", "label": _("Open items"), "fieldtype": "Int", "width": 120},
	]
	try:
		data = frappe.db.sql(
			"""
			SELECT CASE
				WHEN DATE({df}) < CURDATE() THEN 'Past due'
				WHEN DATE({df}) <= DATE_ADD(CURDATE(), INTERVAL 7 DAY) THEN 'Due within 7 days'
				WHEN DATE({df}) <= DATE_ADD(CURDATE(), INTERVAL 30 DAY) THEN 'Due within 30 days'
				ELSE 'Due beyond 30 days'
			END AS severity,
			COUNT(*) AS documents
			FROM {tbl}
			WHERE {where} AND {df} IS NOT NULL
			GROUP BY severity
			ORDER BY FIELD(severity, 'Past due', 'Due within 7 days', 'Due within 30 days', 'Due beyond 30 days')
			""".format(
				tbl=table,
				where=where,
				df=df,
			),
			values,
			as_dict=1,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "kpi_overdue_pressure:{0}".format(ref))
		return _empty(_("Could not load overdue pressure."))
	if not data:
		data = [{"severity": _("No dated open items"), "documents": 0}]
	chart = series_chart(data, "severity", "documents", chart_type="bar")
	past = sum(cint(r.get("documents")) for r in data if r.get("severity") == "Past due")
	summary = [{"label": _("Past due open"), "value": past, "indicator": "red" if past else "green"}]
	return columns, data, None, chart, summary


def kpi_penalty_deposit_exposure(ref, filters, options):
	"""Financial exposure from penalties and deposits where columns exist."""
	table = _table(ref)
	where, values = _base_where(ref, filters)
	has_pen = frappe.db.has_column(ref, "has_penalties")
	has_pest = frappe.db.has_column(ref, "estimated_penalty_amount")
	has_dep = frappe.db.has_column(ref, "deposit_amount")
	if not (has_pen or has_pest or has_dep):
		return _empty(_("No penalty or deposit fields on {0}").format(ref))
	pen_sql = "SUM(CASE WHEN IFNULL(has_penalties,0)=1 THEN 1 ELSE 0 END)" if has_pen else "0"
	amt_pen = "COALESCE(SUM(estimated_penalty_amount),0)" if has_pest else "0"
	amt_dep = "COALESCE(SUM(deposit_amount),0)" if has_dep else "0"
	columns = [
		{"fieldname": "flagged_units", "label": _("Flagged for penalties"), "fieldtype": "Int", "width": 160},
		{"fieldname": "penalty_exposure", "label": _("Penalty exposure"), "fieldtype": "Currency", "width": 160},
		{"fieldname": "deposit_exposure", "label": _("Deposit exposure"), "fieldtype": "Currency", "width": 160},
	]
	try:
		row = frappe.db.sql(
			"""
			SELECT {pen_sql} AS flagged_units,
				{amt_pen} AS penalty_exposure,
				{amt_dep} AS deposit_exposure
			FROM {tbl}
			WHERE {where}
			""".format(
				tbl=table,
				where=where,
				pen_sql=pen_sql,
				amt_pen=amt_pen,
				amt_dep=amt_dep,
			),
			values,
			as_dict=1,
		)[0]
	except Exception:
		frappe.log_error(frappe.get_traceback(), "kpi_penalty_deposit_exposure:{0}".format(ref))
		return _empty(_("Could not load penalty and deposit exposure."))
	data = [row]
	chart = bar_top_numeric(
		[
			{"k": _("Penalty"), "v": flt(row.get("penalty_exposure"))},
			{"k": _("Deposit"), "v": flt(row.get("deposit_exposure"))},
		],
		"k",
		"v",
		dataset_label=_("Currency"),
	)
	summary = [
		{"label": _("Flagged"), "value": cint(row.get("flagged_units")), "indicator": "orange"},
		{"label": _("Penalty exposure"), "value": flt(row.get("penalty_exposure")), "indicator": "red"},
	]
	return columns, data, None, chart, summary


def kpi_simple_count_trend(ref, filters, options):
	"""Lightweight activity trend (count only) when no value column — still a KPI index."""
	grain = options.get("grain") or "week"
	table = _table(ref)
	where, values = _base_where(ref, filters)
	if grain == "month":
		bucket_expr = "DATE_FORMAT(creation, '%%Y-%%m')"
		label = _("Month")
	elif grain == "day":
		bucket_expr = "DATE(creation)"
		label = _("Day")
	else:
		bucket_expr = "YEARWEEK(creation, 3)"
		label = _("Week")
	columns = [
		{"fieldname": "period", "label": label, "fieldtype": "Data", "width": 120},
		{"fieldname": "documents", "label": _("Documents"), "fieldtype": "Int", "width": 100},
	]
	try:
		data = frappe.db.sql(
			"""
			SELECT {b} AS period, COUNT(*) AS documents
			FROM {tbl}
			WHERE {where}
			GROUP BY {b}
			ORDER BY period DESC
			LIMIT 52
			""".format(
				b=bucket_expr,
				tbl=table,
				where=where,
			),
			values,
			as_dict=1,
		)
	except Exception:
		return _empty(_("Could not load activity trend."))
	if not data:
		data = [{"period": _("No data"), "documents": 0}]
	chart = series_chart(data, "period", "documents", chart_type="line")
	summary = [{"label": _("Documents"), "value": sum(cint(r.get("documents")) for r in data), "indicator": "blue"}]
	return columns, data, None, chart, summary


HANDLERS = {
	"executive_snapshot": kpi_executive_snapshot,
	"trend_weekly_value": lambda ref, f, o: kpi_trend_volume_value(ref, f, dict(o or {}, **{"grain": "week"})),
	"trend_monthly_value": lambda ref, f, o: kpi_trend_volume_value(ref, f, dict(o or {}, **{"grain": "month"})),
	"pipeline_mix": kpi_pipeline_mix,
	"top_value": kpi_top_value_concentration,
	"aging_open": kpi_aging_open_backlog,
	"owner_workload": kpi_owner_workload,
	"branch_mix": kpi_branch_profit_view,
	"doc_health": kpi_doc_health_ratio,
	"trend_weekly_count": lambda ref, f, o: kpi_simple_count_trend(ref, f, dict(o or {}, **{"grain": "week"})),
	"trend_monthly_count": lambda ref, f, o: kpi_simple_count_trend(ref, f, dict(o or {}, **{"grain": "month"})),
	"overdue_pressure": kpi_overdue_pressure,
	"penalty_deposit": kpi_penalty_deposit_exposure,
}


def run_management_report(ref_doctype, handler_id, filters=None, options=None):
	"""Dispatch KPI report. ``options`` is a plain dict (from JSON in generated report module)."""
	filters = frappe._dict(filters or {})
	options = options or {}
	if isinstance(options, str):
		try:
			options = json.loads(options) if options else {}
		except Exception:
			options = {}
	fn = HANDLERS.get(handler_id)
	if not fn:
		return _empty(_("Unknown KPI handler: {0}").format(handler_id))
	try:
		return fn(ref_doctype, filters, options)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "run_management_report:{0}:{1}".format(ref_doctype, handler_id))
		return _empty(_("Report failed. Check Error Log."))
