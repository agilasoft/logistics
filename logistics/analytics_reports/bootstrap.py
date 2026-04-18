# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt
"""Shared helpers and named analytics drivers for Script Reports."""

from __future__ import unicode_literals

import re

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate


def _table(doctype):
	return "`tab{0}`".format(doctype.replace("`", ""))


def _valid_field(fieldname):
	return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", fieldname or ""))


def bar_top_numeric(rows, label_field, value_field, limit=12, dataset_label=None):
	"""Bar chart: top N rows by absolute numeric value."""
	if not rows:
		return tally_chart([], label_field, dataset_label=dataset_label)
	sorted_rows = sorted(rows, key=lambda r: abs(flt(r.get(value_field) or 0)), reverse=True)[:limit]
	labels = [str(r.get(label_field) or "")[:60] for r in sorted_rows]
	values = [abs(flt(r.get(value_field))) for r in sorted_rows]
	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": dataset_label or _("Value"), "values": values}],
		},
		"type": "bar",
		"colors": ["#5e64ff"],
	}


def tally_chart(rows, fieldname, dataset_label=None):
	"""Bar chart from frequency of field values (for enriching legacy reports)."""
	from collections import Counter

	if not rows:
		return {
			"data": {"labels": [_("No data")], "datasets": [{"name": dataset_label or _("Count"), "values": [0]}]},
			"type": "bar",
			"colors": ["#5e64ff"],
		}
	c = Counter(str(r.get(fieldname) or _("Unknown")) for r in rows)
	return {
		"data": {
			"labels": list(c.keys()),
			"datasets": [{"name": dataset_label or _("Count"), "values": list(c.values())}],
		},
		"type": "bar",
		"colors": ["#5e64ff"],
	}


def _chart_from_rows(rows, value_field, label_field, chart_type="bar"):
	labels = [str(r.get(label_field) or "") for r in rows]
	values = [flt(r.get(value_field)) for r in rows]
	if not labels:
		labels = [_("No activity")]
		values = [0]
	return {
		"data": {"labels": labels, "datasets": [{"name": _("Count"), "values": values}]},
		"type": chart_type,
		"colors": ["#5e64ff", "#ffa00a", "#28a745", "#007bff", "#6f42c1"],
	}


def series_chart(rows, label_field, value_field, chart_type="bar"):
	"""Bar/line chart where each row supplies label and numeric value columns."""
	if not rows:
		return _chart_from_rows([{label_field: _("No data"), value_field: 0}], value_field, label_field, chart_type)
	return _chart_from_rows(rows, value_field, label_field, chart_type)


def _time_sql(grain):
	if grain == "day":
		return "DATE(creation)", _("Day")
	if grain == "week":
		return "YEARWEEK(creation, 3)", _("Week")
	if grain == "month":
		return "DATE_FORMAT(creation, '%%Y-%%m')", _("Month")
	return "DATE(creation)", _("Day")


def _base_where(ref_doctype, filters):
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
	if frappe.db.has_column(ref_doctype, "docstatus"):
		conditions.append("docstatus < 2")
	return " AND ".join(conditions), values


def run_named_analytics(ref_doctype, mode, filters=None):
	"""Run aggregation report: mode is time:day|time:week|time:month or group:fieldname."""
	filters = frappe._dict(filters or {})
	if not frappe.db.exists("DocType", ref_doctype):
		columns = [{"fieldname": "message", "label": _("Message"), "fieldtype": "Data", "width": 400}]
		data = [{"message": _("DocType not found: {0}").format(ref_doctype)}]
		chart = _chart_from_rows([{"bucket": _("N/A"), "cnt": 0}], "cnt", "bucket")
		return columns, data, None, chart, []

	table = _table(ref_doctype)
	where, values = _base_where(ref_doctype, filters)

	if mode.startswith("time:"):
		grain = mode.split(":", 1)[1]
		group_expr, bucket_label = _time_sql(grain)
	elif mode.startswith("group:"):
		field = mode.split(":", 1)[1]
		if not _valid_field(field) or not frappe.db.has_column(ref_doctype, field):
			group_expr, bucket_label = _time_sql("day")
		else:
			group_expr = "COALESCE(CAST(`{0}` AS CHAR), '')".format(field)
			bucket_label = _(field.replace("_", " ").title())
	else:
		group_expr, bucket_label = _time_sql("day")

	columns = [
		{"fieldname": "bucket", "label": bucket_label, "fieldtype": "Data", "width": 160},
		{"fieldname": "cnt", "label": _("Count"), "fieldtype": "Int", "width": 100},
	]
	try:
		data = frappe.db.sql(
			"""
			SELECT {grp} as bucket, COUNT(*) as cnt
			FROM {tbl}
			WHERE {where}
			GROUP BY {grp}
			ORDER BY bucket DESC
			LIMIT 80
			""".format(
				grp=group_expr,
				tbl=table,
				where=where,
			),
			values,
			as_dict=1,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "named_analytics:{0}:{1}".format(ref_doctype, mode))
		data = []

	if not data:
		data = [{"bucket": _("No records"), "cnt": 0}]

	ctype = "line" if mode.startswith("time:") and "week" in mode else "bar"
	chart = _chart_from_rows(data, "cnt", "bucket", chart_type=ctype)
	total = sum(cint(r.get("cnt")) for r in data)
	summary = [{"label": _("Total documents"), "value": total, "indicator": "blue"}]
	return columns, data, None, chart, summary


def run_analytics_report(ref_doctype, variant, filters=None):
	"""Backward-compatible driver (day / week / month rotation)."""
	modes = ("time:day", "time:week", "time:month")
	return run_named_analytics(ref_doctype, modes[cint(variant) % 3], filters)
