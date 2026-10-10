# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Shared Control Tower engine for module dashboards.

Each tower counts one or more job tables with the same five KPIs used by
Air, Sea, Customs, and Transport: open files, average age, files handled,
milestone lead time, a top breakdown, and returned billings.
"""

from __future__ import unicode_literals

import re

from frappe.utils import cint, flt, getdate, nowdate

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_CLOSED = ("Completed", "Closed", "Cancelled")


def _f():
	import frappe

	return frappe


def _ident(name):
	if not _IDENT.match(name or ""):
		raise ValueError("Invalid SQL identifier: {0}".format(name))
	return name


def _table(doctype):
	if not doctype or "`" in doctype:
		raise ValueError("Invalid DocType")
	return "`tab{0}`".format(doctype)


def _date_sql(source, alias=""):
	field = source["date_field"]
	prefix = "{0}.".format(alias) if alias else ""
	if field == "creation":
		return "DATE({0}`creation`)".format(prefix)
	return "{0}`{1}`".format(prefix, _ident(field))


def _status_sql(source, alias=""):
	prefix = "{0}.".format(alias) if alias else ""
	return "{0}`{1}`".format(prefix, _ident(source["status_field"]))


TOWERS = {
	"warehousing": {
		"title": "Warehousing Control Tower",
		"module": "Warehousing",
		"folder": "warehousing",
		"workspace": "Warehousing",
		"sidebar": "Warehousing",
		"prefix": "whct",
		"prefs_key": "whct_preferences",
		"billing_module": "Warehousing",
		"billing_mode": "module",
		"primary_doctype": "Warehouse Job",
		"roles": ["System Manager", "Warehouse User", "Control Tower Manager", "Control Tower Viewer"],
		"dimension": {
			"mode": "field",
			"field": "type",
			"label": "Job Type",
			"chart": "Top Warehouse Job Types",
			"report": "WHCT Job Type Volumes",
		},
		"sources": [{
			"doctype": "Warehouse Job",
			"label": "Warehouse Job",
			"date_field": "job_open_date",
			"status_field": "job_status",
			"customer_field": "customer",
		}],
	},
	"special_projects": {
		"title": "Special Projects Control Tower",
		"module": "Special Projects",
		"folder": "special_projects",
		"workspace": "Special Projects",
		"sidebar": "Special Projects",
		"prefix": "spct",
		"prefs_key": "spct_preferences",
		"billing_module": "Special Projects",
		"billing_mode": "module",
		"primary_doctype": "Special Project",
		"open_excludes": ("Completed", "Cancelled"),
		"roles": ["System Manager", "Projects Manager", "Control Tower Manager", "Control Tower Viewer"],
		"dimension": {
			"mode": "field",
			"field": "project_type",
			"label": "Project Type",
			"link": "Project Type",
			"chart": "Top Project Types",
			"report": "SPCT Project Type Volumes",
		},
		"sources": [{
			"doctype": "Special Project",
			"label": "Special Project",
			"date_field": "start_date",
			"status_field": "status",
			"customer_field": "customer",
			"milestone_child": "Special Project Milestone",
		}],
	},
	"mice": {
		"title": "MICE Control Tower",
		"module": "MICE",
		"folder": "mice",
		"workspace": "MICE",
		"sidebar": "MICE",
		"prefix": "mict",
		"prefs_key": "mict_preferences",
		"billing_module": "MICE",
		"billing_mode": "module",
		"primary_doctype": "MICE Project",
		"open_excludes": ("Completed", "Cancelled"),
		"roles": ["System Manager", "Projects Manager", "Control Tower Manager", "Control Tower Viewer"],
		"dimension": {
			"mode": "field",
			"field": "exhibit_type",
			"label": "MICE Type",
			"link": "MICE Type",
			"chart": "Top MICE Types",
			"report": "MICT Type Volumes",
		},
		"sources": [{
			"doctype": "MICE Project",
			"label": "MICE Project",
			"date_field": "start_date",
			"status_field": "status",
			"milestone_child": "MICE Project Milestone",
		}],
	},
	"high_value": {
		"title": "High Value Control Tower",
		"module": "High Value",
		"folder": "high_value",
		"workspace": "High Value",
		"sidebar": "High Value",
		"prefix": "hvct",
		"prefs_key": "hvct_preferences",
		"billing_mode": "high_value",
		"primary_doctype": "Air Shipment",
		"roles": ["System Manager", "All", "Control Tower Manager", "Control Tower Viewer"],
		"dimension": {
			"mode": "source",
			"label": "Modality",
			"chart": "High Value by Modality",
			"report": "HVCT Modality Volumes",
		},
		"sources": [
			{"doctype": "Air Shipment", "label": "Air", "date_field": "booking_date", "status_field": "job_status", "customer_field": "customer", "extra_where": "IFNULL(is_high_value, 0) = 1", "milestone_child": "Air Shipment Milestone"},
			{"doctype": "Sea Shipment", "label": "Sea", "date_field": "booking_date", "status_field": "job_status", "customer_field": "customer", "extra_where": "IFNULL(is_high_value, 0) = 1", "milestone_child": "Sea Shipment Milestone"},
			{"doctype": "Transport Job", "label": "Transport", "date_field": "booking_date", "status_field": "status", "customer_field": "customer", "extra_where": "IFNULL(is_high_value, 0) = 1", "milestone_child": "Transport Job Milestone"},
			{"doctype": "Declaration", "label": "Customs", "date_field": "declaration_date", "status_field": "job_status", "customer_field": "customer", "extra_where": "IFNULL(is_high_value, 0) = 1", "milestone_child": "Declaration Milestone"},
			{"doctype": "Warehouse Job", "label": "Warehouse", "date_field": "job_open_date", "status_field": "job_status", "customer_field": "customer", "extra_where": "IFNULL(is_high_value, 0) = 1"},
		],
	},
	"time_sensitive": {
		"title": "Time Sensitive Control Tower",
		"module": "Time Sensitive",
		"folder": "time_sensitive",
		"workspace": "Time Sensitive",
		"sidebar": "Time Sensitive",
		"prefix": "tsct",
		"prefs_key": "tsct_preferences",
		"billing_module": "Time Sensitive",
		"billing_mode": "module",
		"primary_doctype": "Time Sensitive Case",
		"open_excludes": ("Delivered", "Closed", "Cancelled"),
		"roles": ["System Manager", "Time Sensitive Manager", "Time Sensitive Coordinator", "Time Sensitive Viewer", "Control Tower Manager", "Control Tower Viewer"],
		"dimension": {
			"mode": "field",
			"field": "case_type",
			"label": "Case Type",
			"link": "Time Sensitive Case Type",
			"chart": "Top Case Types",
			"report": "TSCT Case Type Volumes",
		},
		"sources": [{
			"doctype": "Time Sensitive Case",
			"label": "Time Sensitive Case",
			"date_field": "creation",
			"status_field": "status",
			"customer_field": "customer",
			"milestone_child": "Time Sensitive Case Milestone",
		}],
	},
	"sustainability": {
		"title": "Sustainability Control Tower",
		"module": "Sustainability",
		"folder": "sustainability",
		"workspace": "Sustainability",
		"sidebar": "Sustainability",
		"prefix": "suct",
		"prefs_key": "suct_preferences",
		"billing_module": "Sustainability",
		"billing_mode": "module",
		"primary_doctype": "Carbon Footprint",
		"open_excludes": ("Verified", "Failed Verification"),
		"roles": ["System Manager", "Accounts User", "Control Tower Manager", "Control Tower Viewer"],
		"lead_time": "date_diff",
		"lead_end_field": "verification_date",
		"measure_field": "total_emissions",
		"measure_label": "Emissions",
		"dimension": {
			"mode": "field",
			"field": "module",
			"label": "Module",
			"chart": "Carbon Footprint by Module",
			"report": "SUCT Module Volumes",
		},
		"sources": [{
			"doctype": "Carbon Footprint",
			"label": "Carbon Footprint",
			"date_field": "date",
			"status_field": "verification_status",
		}],
	},
	"pricing_center": {
		"title": "Pricing Center Control Tower",
		"module": "Pricing Center",
		"folder": "pricing_center",
		"workspace": "Pricing",
		"sidebar": "Pricing Center",
		"prefix": "pcct",
		"prefs_key": "pcct_preferences",
		"billing_module": "Pricing Center",
		"billing_mode": "module",
		"primary_doctype": "Sales Quote",
		"open_excludes": ("Converted",),
		"roles": ["System Manager", "Control Tower Manager", "Control Tower Viewer"],
		"dimension": {
			"mode": "field",
			"field": "main_service",
			"label": "Service",
			"chart": "Quotes by Service",
			"report": "PCCT Service Volumes",
		},
		"sources": [{
			"doctype": "Sales Quote",
			"label": "Sales Quote",
			"date_field": "date",
			"status_field": "status",
			"customer_field": "customer",
		}],
	},
}


def get_tower(key):
	tower = TOWERS.get(key)
	if not tower:
		raise KeyError(key)
	return tower


def _excludes(tower):
	return tuple(tower.get("open_excludes") or _CLOSED)


def _default_date_range(fiscal_year=None):
	year = cint(fiscal_year) or cint(nowdate()[:4])
	from_date = "{0}-01-01".format(year)
	today = nowdate()
	year_end = "{0}-12-31".format(year)
	to_date = today if str(today)[:4] == str(year) else year_end
	return from_date, to_date


def _parse_filters(filters=None, company=None, branch=None, cost_center=None,
		profit_center=None, dimension=None, fiscal_year=None, from_date=None, to_date=None):
	if isinstance(filters, str):
		filters = _f().parse_json(filters) or {}
	if not isinstance(filters, dict):
		filters = {}
	out = {
		"company": (filters.get("company") or company or "").strip(),
		"branch": (filters.get("branch") or branch or "").strip(),
		"cost_center": (filters.get("cost_center") or cost_center or "").strip(),
		"profit_center": (filters.get("profit_center") or profit_center or "").strip(),
		"dimension": (filters.get("dimension") or dimension or "").strip(),
	}
	fy = filters.get("fiscal_year") or fiscal_year
	out["fiscal_year"] = int(fy) if fy else int(nowdate()[:4])
	fd = filters.get("from_date") or from_date
	td = filters.get("to_date") or to_date
	if not fd or not td:
		default_from, default_to = _default_date_range(out["fiscal_year"])
		fd = fd or default_from
		td = td or default_to
	fd, td = getdate(fd), getdate(td)
	if fd > td:
		fd, td = td, fd
	out["from_date"] = str(fd)
	out["to_date"] = str(td)
	return out


def _dim_clauses(filters, alias=""):
	prefix = "{0}.".format(alias) if alias else ""
	conditions, values = [], []
	for key in ("company", "branch", "cost_center", "profit_center"):
		val = filters.get(key)
		if not val:
			continue
		conditions.append("{0}`{1}` = %s".format(prefix, _ident(key)))
		values.append(val)
	return conditions, values


def _selected_sources(tower, filters):
	sources = list(tower["sources"])
	wanted = (filters.get("dimension") or "").strip()
	dimension = tower["dimension"]
	if wanted and dimension.get("mode") == "source":
		sources = [source for source in sources if source["label"] == wanted]
	return sources


def _where(source, filters, alias="", extra_parts=None, extra_values=None, include_dimension=True):
	conditions, values = _dim_clauses(filters, alias=alias)
	if source.get("extra_where"):
		clause = source["extra_where"]
		if alias:
			clause = clause.replace("is_high_value", "{0}.is_high_value".format(alias))
		conditions.append(clause)
	dimension = None
	if include_dimension:
		# Field dimensions are applied by the caller when the query is about that field.
		pass
	if extra_parts:
		conditions.extend(extra_parts)
		values.extend(extra_values or [])
	return conditions, values


def _field_dimension_clause(tower, filters, alias=""):
	dimension = tower["dimension"]
	value = (filters.get("dimension") or "").strip()
	if dimension.get("mode") != "field" or not value:
		return [], []
	prefix = "{0}.".format(alias) if alias else ""
	return ["{0}`{1}` = %s".format(prefix, _ident(dimension["field"]))], [value]


def _run(query, values, as_dict=False, title="module_tower"):
	try:
		return _f().db.sql(query, tuple(values), as_dict=as_dict)
	except Exception:
		_f().log_error(_f().get_traceback(), title)
		return []


def _source_counts(tower, filters):
	today = nowdate()
	from_date, to_date = filters["from_date"], filters["to_date"]
	excludes = _excludes(tower)
	rows = []
	open_total = 0
	age_sum = 0
	handled_total = 0
	for source in _selected_sources(tower, filters):
		dim_c, dim_v = _where(source, filters)
		field_c, field_v = _field_dimension_clause(tower, filters)
		placeholders = ", ".join(["%s"] * len(excludes))
		open_where = dim_c + field_c + ["{0} NOT IN ({1})".format(_status_sql(source), placeholders)]
		open_values = [today] + dim_v + field_v + list(excludes)
		open_rs = _run(
			"""
			SELECT COUNT(*) AS n, SUM(GREATEST(DATEDIFF(%s, {date}), 0)) AS age_sum
			FROM {table}
			WHERE {where}
			""".format(
				date=_date_sql(source),
				table=_table(source["doctype"]),
				where=" AND ".join(open_where),
			),
			open_values,
			title="module_tower_open",
		)
		open_n = int(open_rs[0][0]) if open_rs and open_rs[0] and open_rs[0][0] is not None else 0
		open_age = int(open_rs[0][1]) if open_rs and open_rs[0] and open_rs[0][1] is not None else 0
		handled_where = dim_c + field_c + ["{0} BETWEEN %s AND %s".format(_date_sql(source))]
		handled_values = dim_v + field_v + [from_date, to_date]
		handled_rs = _run(
			"SELECT COUNT(*) FROM {table} WHERE {where}".format(
				table=_table(source["doctype"]),
				where=" AND ".join(handled_where),
			),
			handled_values,
			title="module_tower_handled",
		)
		handled_n = int(handled_rs[0][0]) if handled_rs and handled_rs[0] and handled_rs[0][0] is not None else 0
		open_total += open_n
		age_sum += open_age
		handled_total += handled_n
		rows.append({
			"module": source["label"],
			"open": open_n,
			"handled": handled_n,
			"open_avg_age": round((open_age / open_n), 1) if open_n else 0.0,
		})
	avg_age = (age_sum / open_total) if open_total else 0.0
	return {
		"open_job_files_count": open_total,
		"avg_age_open_jobs": avg_age,
		"jobs_handled_count": handled_total,
		"by_module": rows,
	}


def _avg_lead_time(tower, filters):
	if tower.get("lead_time") == "date_diff":
		return _date_diff_lead_time(tower, filters)
	total_sec = 0.0
	total_n = 0
	for source in _selected_sources(tower, filters):
		child = source.get("milestone_child")
		if not child:
			continue
		if not _f().db.exists("DocType", child):
			continue
		dim_c, dim_v = _where(source, filters, alias="p")
		field_c, field_v = _field_dimension_clause(tower, filters, alias="p")
		parts = dim_c + field_c + ["{0} BETWEEN %s AND %s".format(_date_sql(source, alias="p"))]
		values = [source["doctype"]] + dim_v + field_v + [filters["from_date"], filters["to_date"]]
		rs = _run(
			"""
			SELECT SUM(TIMESTAMPDIFF(SECOND, COALESCE(c.planned_end, c.planned_start), COALESCE(c.actual_end, c.actual_start))) AS sum_sec,
			       COUNT(*) AS n
			FROM {child} c
			JOIN {parent} p ON p.name = c.parent
			WHERE c.parenttype = %s
			  AND (c.actual_end IS NOT NULL OR c.actual_start IS NOT NULL)
			  AND (c.planned_end IS NOT NULL OR c.planned_start IS NOT NULL)
			  AND {extra}
			""".format(
				child=_table(child),
				parent=_table(source["doctype"]),
				extra=" AND ".join(parts),
			),
			values,
			title="module_tower_lead",
		)
		total_sec += flt(rs[0][0]) if rs and rs[0] and rs[0][0] is not None else 0.0
		total_n += int(rs[0][1]) if rs and rs[0] and rs[0][1] is not None else 0
	if not total_n:
		return 0.0
	return (total_sec / total_n) / 86400.0


def _date_diff_lead_time(tower, filters):
	end_field = _ident(tower["lead_end_field"])
	total_days = 0.0
	total_n = 0
	for source in _selected_sources(tower, filters):
		dim_c, dim_v = _where(source, filters)
		field_c, field_v = _field_dimension_clause(tower, filters)
		parts = dim_c + field_c + [
			"`{0}` IS NOT NULL".format(end_field),
			"{0} IS NOT NULL".format(_date_sql(source)),
			"{0} BETWEEN %s AND %s".format(_date_sql(source)),
		]
		values = dim_v + field_v + [filters["from_date"], filters["to_date"]]
		rs = _run(
			"""
			SELECT SUM(DATEDIFF(`{end}`, {start})) AS sum_days, COUNT(*) AS n
			FROM {table}
			WHERE {where}
			""".format(
				end=end_field,
				start=_date_sql(source),
				table=_table(source["doctype"]),
				where=" AND ".join(parts),
			),
			values,
			title="module_tower_date_lead",
		)
		total_days += flt(rs[0][0]) if rs and rs[0] and rs[0][0] is not None else 0.0
		total_n += int(rs[0][1]) if rs and rs[0] and rs[0][1] is not None else 0
	if not total_n:
		return 0.0
	return total_days / total_n


def _top_dimension(tower, filters, limit):
	dimension = tower["dimension"]
	if dimension.get("mode") == "source":
		rows = []
		for row in _source_counts(tower, filters)["by_module"]:
			rows.append({"label": row["module"], "value": flt(row["handled"])})
		rows.sort(key=lambda row: row["value"], reverse=True)
		return rows[:limit]
	field = _ident(dimension["field"])
	combined = {}
	for source in _selected_sources(tower, filters):
		dim_c, dim_v = _where(source, filters)
		field_c, field_v = _field_dimension_clause(tower, filters)
		parts = dim_c + field_c + [
			"{0} BETWEEN %s AND %s".format(_date_sql(source)),
			"IFNULL(`{0}`, '') != ''".format(field),
		]
		values = dim_v + field_v + [filters["from_date"], filters["to_date"], limit]
		rs = _run(
			"""
			SELECT `{field}` AS label, COUNT(*) AS value
			FROM {table}
			WHERE {where}
			GROUP BY `{field}`
			ORDER BY value DESC
			LIMIT %s
			""".format(field=field, table=_table(source["doctype"]), where=" AND ".join(parts)),
			values,
			as_dict=True,
			title="module_tower_top",
		)
		for row in rs or []:
			label = row.get("label") or ""
			combined[label] = combined.get(label, 0) + flt(row.get("value"))
	ranked = [{"label": label, "value": value} for label, value in combined.items()]
	ranked.sort(key=lambda row: row["value"], reverse=True)
	return ranked[:limit]


def _returned_count(tower, filters):
	if not _f().db.exists("DocType", "Returned Billing"):
		return 0
	dim_c, dim_v = _dim_clauses(filters)
	conditions = dim_c + ["returned_on BETWEEN %s AND %s"]
	values = dim_v + [filters["from_date"], filters["to_date"]]
	mode = tower.get("billing_mode")
	if mode == "module" and _f().db.has_column("Returned Billing", "module"):
		conditions.append("module = %s")
		values.append(tower.get("billing_module") or tower["module"])
	elif mode == "high_value":
		exists = []
		for source in tower["sources"]:
			exists.append(
				"EXISTS (SELECT 1 FROM {table} s WHERE s.name = `tabReturned Billing`.job_no AND IFNULL(s.is_high_value, 0) = 1)".format(
					table=_table(source["doctype"])
				)
			)
		conditions.append("(IFNULL(job_no, '') != '' AND ({0}))".format(" OR ".join(exists)))
	rs = _run(
		"SELECT COUNT(*) FROM `tabReturned Billing` WHERE {0}".format(" AND ".join(conditions)),
		values,
		title="module_tower_returned",
	)
	return int(rs[0][0]) if rs and rs[0] and rs[0][0] is not None else 0


def _clamp_limit(n):
	return max(1, min(50, cint(n) or 10))


def _reports(tower):
	prefix = tower["prefix"].upper()
	return {
		"job_files": "{0} Job Files Detail".format(prefix),
		"lead_time": "{0} Milestone Lead Time".format(prefix),
		"volumes": tower["dimension"]["report"],
		"returned": "{0} Returned Billings".format(prefix),
		"snapshot": "{0} Module Snapshot".format(prefix),
	}


def module_snapshot_rows(key, filters=None):
	tower = get_tower(key)
	parsed = _parse_filters(filters)
	return _source_counts(tower, parsed)["by_module"]


def number_card_value(key, filters=None):
	tower = get_tower(key)
	reports = _reports(tower)
	specs = {
		"open_job_files_count": (reports["job_files"], "Int", {"scope": "Open"}),
		"avg_age_open_jobs": (reports["job_files"], "Float", {"scope": "Open"}),
		"jobs_handled_count": (reports["job_files"], "Int", {"scope": "Handled"}),
		"avg_lead_time_per_milestone": (reports["lead_time"], "Float", {}),
		"returned_billings_count": (reports["returned"], "Int", {}),
	}
	raw = filters
	if isinstance(raw, str):
		raw = _f().parse_json(raw) or {}
	if not isinstance(raw, dict):
		raw = {}
	raw = dict(raw)
	metric = (raw.pop("metric", None) or "").strip()
	spec = specs.get(metric)
	if not spec:
		return {"value": 0, "fieldtype": "Int"}
	if not (raw.get("company") or "").strip():
		raw["company"] = _f().defaults.get_user_default("Company") or ""
	parsed = _parse_filters(raw)
	if metric in ("open_job_files_count", "avg_age_open_jobs", "jobs_handled_count"):
		value = _source_counts(tower, parsed).get(metric) or 0
	elif metric == "avg_lead_time_per_milestone":
		value = _avg_lead_time(tower, parsed)
	else:
		value = _returned_count(tower, parsed)
	fieldtype = spec[1]
	value = int(value or 0) if fieldtype == "Int" else round(flt(value or 0), 1)
	options = {
		"fiscal_year": parsed["fiscal_year"],
		"from_date": parsed["from_date"],
		"to_date": parsed["to_date"],
	}
	if parsed.get("company"):
		options["company"] = parsed["company"]
	for name in ("branch", "cost_center", "profit_center", "dimension"):
		if parsed.get(name):
			options[name] = parsed[name]
	options.update(spec[2])
	return {
		"value": value,
		"fieldtype": fieldtype,
		"route": ["query-report", spec[0]],
		"route_options": options,
	}


def get_dashboard_data(key, filters=None, dimension_limit=None, **kwargs):
	tower = get_tower(key)
	parsed = _parse_filters(filters, **{name: kwargs.get(name) for name in (
		"company", "branch", "cost_center", "profit_center", "dimension", "fiscal_year", "from_date", "to_date",
	)})
	limit = _clamp_limit(dimension_limit if dimension_limit not in (None, "") else 10)
	kpis = _source_counts(tower, parsed)
	top = _top_dimension(tower, parsed, limit)
	return {
		"filters": parsed,
		"from_date": parsed["from_date"],
		"to_date": parsed["to_date"],
		"kpis": {
			"open_job_files_count": int(kpis["open_job_files_count"]),
			"avg_age_open_jobs": round(flt(kpis["avg_age_open_jobs"]), 1),
			"jobs_handled_count": int(kpis["jobs_handled_count"]),
			"avg_lead_time_per_milestone": round(flt(_avg_lead_time(tower, parsed)), 1),
			"returned_billings_count": int(_returned_count(tower, parsed)),
		},
		"top": top,
		"by_module": kpis["by_module"],
		"links": _reports(tower),
		"dimension_limit": limit,
	}


def _normalize_report_filters(filters=None):
	filters = _f()._dict(filters or {})
	if "company" not in filters:
		company = (_f().defaults.get_user_default("Company") or "").strip()
	else:
		company = (filters.get("company") or "").strip()
	out = {
		"company": company,
		"branch": (filters.get("branch") or "").strip(),
		"cost_center": (filters.get("cost_center") or "").strip(),
		"profit_center": (filters.get("profit_center") or "").strip(),
		"dimension": (filters.get("dimension") or "").strip(),
		"scope": (filters.get("scope") or "Open").strip() or "Open",
		"fiscal_year": cint(filters.get("fiscal_year")) or cint(nowdate()[:4]),
		"limit": _clamp_limit(filters.get("limit") or 10),
	}
	return _parse_filters(out) | {"scope": out["scope"], "limit": out["limit"]}


def job_files_execute(key, filters=None):
	frappe = _f()
	_ = frappe._
	tower = get_tower(key)
	parsed = _normalize_report_filters(filters)
	dimension = tower["dimension"]
	columns = [
		{"fieldname": "name", "label": _("Record"), "fieldtype": "Dynamic Link", "options": "source_doctype", "width": 160},
		{"fieldname": "source_doctype", "label": _("DocType"), "fieldtype": "Data", "width": 140},
		{"fieldname": "source", "label": _("Source"), "fieldtype": "Data", "width": 140},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 120},
		{"fieldname": "record_date", "label": _("Date"), "fieldtype": "Date", "width": 110},
		{"fieldname": "age_days", "label": _("Age (days)"), "fieldtype": "Int", "width": 100},
		{"fieldname": "dimension", "label": _(dimension["label"]), "fieldtype": "Data", "width": 140},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 160},
		{"fieldname": "company", "label": _("Company"), "fieldtype": "Link", "options": "Company", "width": 140},
		{"fieldname": "branch", "label": _("Branch"), "fieldtype": "Link", "options": "Branch", "width": 120},
	]
	rows = []
	excludes = _excludes(tower)
	today = nowdate()
	for source in _selected_sources(tower, parsed):
		dim_c, dim_v = _where(source, parsed)
		field_c, field_v = _field_dimension_clause(tower, parsed)
		conditions = list(dim_c) + list(field_c)
		values = list(dim_v) + list(field_v)
		scope = parsed.get("scope")
		placeholders = ", ".join(["%s"] * len(excludes))
		if scope == "Open":
			conditions.append("{0} NOT IN ({1})".format(_status_sql(source), placeholders))
			values.extend(excludes)
		elif scope == "Handled":
			conditions.append("{0} BETWEEN %s AND %s".format(_date_sql(source)))
			values.extend([parsed["from_date"], parsed["to_date"]])
		else:
			conditions.append("({status} NOT IN ({ph}) OR {date} BETWEEN %s AND %s)".format(
				status=_status_sql(source), ph=placeholders, date=_date_sql(source),
			))
			values.extend(list(excludes) + [parsed["from_date"], parsed["to_date"]])
		customer = "`{0}`".format(_ident(source["customer_field"])) if source.get("customer_field") else "''"
		dimension_sql = "'{0}'".format(source["label"].replace("'", "")) if dimension.get("mode") == "source" else "IFNULL(`{0}`, '')".format(_ident(dimension["field"]))
		rs = _run(
			"""
			SELECT name, {status} AS status, {date} AS record_date,
			       {customer} AS customer, company, branch,
			       {dimension} AS dimension,
			       GREATEST(DATEDIFF(%s, {date}), 0) AS age_days
			FROM {table}
			WHERE {where}
			ORDER BY record_date DESC
			LIMIT 1000
			""".format(
				status=_status_sql(source),
				date=_date_sql(source),
				customer=customer,
				dimension=dimension_sql,
				table=_table(source["doctype"]),
				where=" AND ".join(conditions) or "1=1",
			),
			[today] + values,
			as_dict=True,
			title="module_tower_job_files",
		)
		for row in rs or []:
			row["source_doctype"] = source["doctype"]
			row["source"] = source["label"]
			rows.append(row)
	return columns, rows, None, None, [
		{"label": _("Rows"), "value": len(rows), "datatype": "Int"},
		{"label": _("Scope"), "value": parsed.get("scope"), "datatype": "Data"},
	]


def lead_time_execute(key, filters=None):
	frappe = _f()
	_ = frappe._
	tower = get_tower(key)
	parsed = _normalize_report_filters(filters)
	columns = [
		{"fieldname": "source", "label": _("Source"), "fieldtype": "Data", "width": 140},
		{"fieldname": "record", "label": _("Record"), "fieldtype": "Dynamic Link", "options": "source_doctype", "width": 160},
		{"fieldname": "source_doctype", "label": _("DocType"), "fieldtype": "Data", "width": 140},
		{"fieldname": "milestone", "label": _("Milestone"), "fieldtype": "Data", "width": 160},
		{"fieldname": "lead_time_days", "label": _("Lead Time (days)"), "fieldtype": "Float", "width": 130},
	]
	if tower.get("lead_time") == "date_diff":
		return _date_diff_lead_report(tower, parsed, columns)
	rows = []
	has_milestone = False
	for source in _selected_sources(tower, parsed):
		child = source.get("milestone_child")
		if not child or not frappe.db.exists("DocType", child):
			continue
		has_milestone = True
		dim_c, dim_v = _where(source, parsed, alias="p")
		field_c, field_v = _field_dimension_clause(tower, parsed, alias="p")
		parts = dim_c + field_c + ["{0} BETWEEN %s AND %s".format(_date_sql(source, alias="p"))]
		values = [source["doctype"]] + dim_v + field_v + [parsed["from_date"], parsed["to_date"]]
		rs = _run(
			"""
			SELECT p.name AS record, c.milestone,
			       TIMESTAMPDIFF(SECOND, COALESCE(c.planned_end, c.planned_start), COALESCE(c.actual_end, c.actual_start)) / 86400.0 AS lead_time_days
			FROM {child} c
			JOIN {parent} p ON p.name = c.parent
			WHERE c.parenttype = %s
			  AND (c.actual_end IS NOT NULL OR c.actual_start IS NOT NULL)
			  AND (c.planned_end IS NOT NULL OR c.planned_start IS NOT NULL)
			  AND {extra}
			LIMIT 1000
			""".format(child=_table(child), parent=_table(source["doctype"]), extra=" AND ".join(parts)),
			values,
			as_dict=True,
			title="module_tower_lead_report",
		)
		for row in rs or []:
			row["source"] = source["label"]
			row["source_doctype"] = source["doctype"]
			row["lead_time_days"] = round(flt(row.get("lead_time_days")), 2)
			rows.append(row)
	message = None if has_milestone else _("This module has no milestone table.")
	return columns, rows, message, None, [
		{"label": _("Milestones"), "value": len(rows), "datatype": "Int"},
	]


def _date_diff_lead_report(tower, parsed, columns):
	_ = _f()._
	end_field = _ident(tower["lead_end_field"])
	rows = []
	for source in _selected_sources(tower, parsed):
		dim_c, dim_v = _where(source, parsed)
		field_c, field_v = _field_dimension_clause(tower, parsed)
		parts = dim_c + field_c + [
			"`{0}` IS NOT NULL".format(end_field),
			"{0} BETWEEN %s AND %s".format(_date_sql(source)),
		]
		values = dim_v + field_v + [parsed["from_date"], parsed["to_date"]]
		rs = _run(
			"""
			SELECT name AS record, DATEDIFF(`{end}`, {start}) AS lead_time_days
			FROM {table}
			WHERE {where}
			LIMIT 1000
			""".format(
				end=end_field,
				start=_date_sql(source),
				table=_table(source["doctype"]),
				where=" AND ".join(parts),
			),
			values,
			as_dict=True,
			title="module_tower_date_lead_report",
		)
		for row in rs or []:
			row["source"] = source["label"]
			row["source_doctype"] = source["doctype"]
			row["milestone"] = _("Verification")
			row["lead_time_days"] = round(flt(row.get("lead_time_days")), 2)
			rows.append(row)
	return columns, rows, None, None, [{"label": _("Rows"), "value": len(rows), "datatype": "Int"}]


def volumes_execute(key, filters=None):
	frappe = _f()
	_ = frappe._
	tower = get_tower(key)
	parsed = _normalize_report_filters(filters)
	dimension = tower["dimension"]
	columns = [
		{"fieldname": "label", "label": _(dimension["label"]), "fieldtype": "Data", "width": 180},
		{"fieldname": "job_count", "label": _("Count"), "fieldtype": "Int", "width": 100},
		{"fieldname": "open_count", "label": _("Open"), "fieldtype": "Int", "width": 90},
		{"fieldname": "pct_of_total", "label": _("% of Total"), "fieldtype": "Percent", "width": 100},
	]
	if dimension.get("mode") == "source":
		counts = _source_counts(tower, parsed)["by_module"]
		rows = [{"label": row["module"], "job_count": row["handled"], "open_count": row["open"]} for row in counts]
	else:
		field = _ident(dimension["field"])
		combined = {}
		for source in _selected_sources(tower, parsed):
			dim_c, dim_v = _where(source, parsed)
			field_c, field_v = _field_dimension_clause(tower, parsed)
			parts = dim_c + field_c + [
				"{0} BETWEEN %s AND %s".format(_date_sql(source)),
				"IFNULL(`{0}`, '') != ''".format(field),
			]
			open_case = "{0} NOT IN ({1})".format(_status_sql(source), ", ".join(["%s"] * len(_excludes(tower))))
			# SELECT CASE placeholders appear before the WHERE clause, then LIMIT.
			values = list(_excludes(tower)) + dim_v + field_v + [parsed["from_date"], parsed["to_date"], parsed["limit"]]
			rs = _run(
				"""
				SELECT `{field}` AS label, COUNT(*) AS job_count,
				       SUM(CASE WHEN {open_case} THEN 1 ELSE 0 END) AS open_count
				FROM {table}
				WHERE {where}
				GROUP BY `{field}`
				ORDER BY job_count DESC
				LIMIT %s
				""".format(
					field=field,
					open_case=open_case,
					table=_table(source["doctype"]),
					where=" AND ".join(parts),
				),
				values,
				as_dict=True,
				title="module_tower_volumes",
			)
			for row in rs or []:
				label = row.get("label") or ""
				bucket = combined.setdefault(label, {"label": label, "job_count": 0, "open_count": 0})
				bucket["job_count"] += int(row.get("job_count") or 0)
				bucket["open_count"] += int(row.get("open_count") or 0)
		rows = sorted(combined.values(), key=lambda row: row["job_count"], reverse=True)[: parsed["limit"]]
	total = sum(flt(row.get("job_count")) for row in rows) or 1
	for row in rows:
		row["pct_of_total"] = round((flt(row.get("job_count")) / total) * 100.0, 1)
	chart = {
		"data": {
			"labels": [row.get("label") or "" for row in rows],
			"datasets": [{"name": _("Count"), "values": [flt(row.get("job_count")) for row in rows]}],
		},
		"type": "bar",
		"title": dimension["chart"],
	}
	return columns, rows, None, chart, [{"label": _("Groups"), "value": len(rows), "datatype": "Int"}]


def returned_execute(key, filters=None):
	frappe = _f()
	_ = frappe._
	tower = get_tower(key)
	parsed = _normalize_report_filters(filters)
	columns = [
		{"fieldname": "name", "label": _("Returned Billing"), "fieldtype": "Link", "options": "Returned Billing", "width": 140},
		{"fieldname": "returned_on", "label": _("Returned On"), "fieldtype": "Date", "width": 110},
		{"fieldname": "resolution_status", "label": _("Status"), "fieldtype": "Data", "width": 110},
		{"fieldname": "module", "label": _("Module"), "fieldtype": "Data", "width": 120},
		{"fieldname": "job_no", "label": _("Job"), "fieldtype": "Data", "width": 140},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 160},
		{"fieldname": "company", "label": _("Company"), "fieldtype": "Link", "options": "Company", "width": 140},
	]
	if not frappe.db.exists("DocType", "Returned Billing"):
		return columns, [], _("Returned Billing DocType is not installed."), None, []
	dim_c, dim_v = _dim_clauses(parsed)
	conditions = dim_c + ["returned_on BETWEEN %s AND %s"]
	values = dim_v + [parsed["from_date"], parsed["to_date"]]
	if tower.get("billing_mode") == "module" and frappe.db.has_column("Returned Billing", "module"):
		conditions.append("module = %s")
		values.append(tower.get("billing_module") or tower["module"])
	elif tower.get("billing_mode") == "high_value":
		exists = [
			"EXISTS (SELECT 1 FROM {table} s WHERE s.name = `tabReturned Billing`.job_no AND IFNULL(s.is_high_value, 0) = 1)".format(
				table=_table(source["doctype"])
			)
			for source in tower["sources"]
		]
		conditions.append("(IFNULL(job_no, '') != '' AND ({0}))".format(" OR ".join(exists)))
	rows = _run(
		"""
		SELECT name, returned_on, resolution_status, module, job_no, customer, company
		FROM `tabReturned Billing`
		WHERE {where}
		ORDER BY returned_on DESC
		LIMIT 1000
		""".format(where=" AND ".join(conditions)),
		values,
		as_dict=True,
		title="module_tower_returned_report",
	)
	return columns, rows or [], None, None, [{"label": _("Returned"), "value": len(rows or []), "datatype": "Int"}]


def snapshot_execute(key, filters=None):
	frappe = _f()
	_ = frappe._
	parsed = _normalize_report_filters(filters)
	rows = module_snapshot_rows(key, parsed)
	columns = [
		{"fieldname": "module", "label": _("Module"), "fieldtype": "Data", "width": 180},
		{"fieldname": "open", "label": _("Open"), "fieldtype": "Int", "width": 100},
		{"fieldname": "open_avg_age", "label": _("Avg age"), "fieldtype": "Float", "width": 110},
		{"fieldname": "handled", "label": _("Handled"), "fieldtype": "Int", "width": 110},
	]
	chart = {
		"data": {
			"labels": [row.get("module") or "" for row in rows],
			"datasets": [
				{"name": _("Open"), "values": [row.get("open") or 0 for row in rows]},
				{"name": _("Handled"), "values": [row.get("handled") or 0 for row in rows]},
			],
		},
		"type": "bar",
		"title": _("Open vs Handled"),
	}
	return columns, rows, None, chart, [
		{"label": _("Open"), "value": int(sum(row.get("open") or 0 for row in rows)), "datatype": "Int"},
		{"label": _("Handled"), "value": int(sum(row.get("handled") or 0 for row in rows)), "datatype": "Int"},
	]
