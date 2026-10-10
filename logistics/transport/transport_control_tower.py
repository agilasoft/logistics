# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Transport Control Tower dashboard API.

Aggregates transport operational KPIs for the Transport Control Tower
dashboard, filtered by Company / Branch / Cost Center / Profit Center /
Vehicle Type:

- Number of open transport jobs
- Average age of open transport jobs
- Number of transport jobs handled in the selected period
- Average lead time per milestone
- Top vehicle types (limit is a per-user preference)
- Number of returned billings in the selected period
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

OPEN_EXCLUDES = ("Completed", "Closed", "Cancelled")
TRANSPORT_JOB = "Transport Job"
TRANSPORT_MILESTONE = "Transport Job Milestone"
PREFS_KEY = "tct_preferences"
DEFAULT_VEHICLE_TYPE_LIMIT = 10
MAX_VEHICLE_TYPE_LIMIT = 50

DEFAULT_PREFERENCES = {
	"kpis": {
		"show_open_jobs": 1,
		"show_avg_age": 1,
		"show_handled": 1,
		"show_lead_time": 1,
		"warn_age_days": 60,
	},
	"vehicle_types": {
		"limit": DEFAULT_VEHICLE_TYPE_LIMIT,
	},
	"returned": {
		"visible": 1,
	},
	"modules": {
		"visible": 1,
	},
	"links": {
		"visible": 1,
	},
}


def _clamp_vehicle_type_limit(n):
	n = cint(n) or DEFAULT_VEHICLE_TYPE_LIMIT
	return max(1, min(MAX_VEHICLE_TYPE_LIMIT, n))


def _merge_preferences(raw=None):
	"""Return a full prefs dict with defaults filled in."""
	prefs = frappe.parse_json(raw) if isinstance(raw, str) else (raw or {})
	if not isinstance(prefs, dict):
		prefs = {}
	out = frappe._dict()
	for section, defaults in DEFAULT_PREFERENCES.items():
		section_vals = prefs.get(section) if isinstance(prefs.get(section), dict) else {}
		merged = dict(defaults)
		merged.update({k: section_vals[k] for k in defaults if k in section_vals})
		out[section] = merged
	out["vehicle_types"]["limit"] = _clamp_vehicle_type_limit(out["vehicle_types"].get("limit"))
	out["kpis"]["warn_age_days"] = max(0, cint(out["kpis"].get("warn_age_days") or 0))
	for key in ("show_open_jobs", "show_avg_age", "show_handled", "show_lead_time"):
		out["kpis"][key] = 1 if cint(out["kpis"].get(key)) else 0
	for section in ("returned", "modules", "links"):
		out[section]["visible"] = 1 if cint(out[section].get("visible")) else 0
	return out


def _default_date_range(fiscal_year=None):
	"""Return (from_date, to_date) for a fiscal/calendar year."""
	year = cint(fiscal_year) or cint(nowdate()[:4])
	from_date = "{0}-01-01".format(year)
	today = nowdate()
	year_end = "{0}-12-31".format(year)
	to_date = today if str(today)[:4] == str(year) else year_end
	return from_date, to_date


def _date_bounds(filters):
	"""Effective booking/returned date window from filters."""
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	if from_date and to_date:
		fd, td = getdate(from_date), getdate(to_date)
		if fd > td:
			fd, td = td, fd
		return str(fd), str(td)
	return _default_date_range(filters.get("fiscal_year"))


def _parse_filters(filters=None, company=None, branch=None, cost_center=None,
		profit_center=None, vehicle_type=None, fiscal_year=None, from_date=None, to_date=None):
	"""Normalize whitelist args into a filter dict."""
	if isinstance(filters, str):
		filters = frappe.parse_json(filters) or {}
	if not isinstance(filters, dict):
		filters = {}

	out = {
		"company": (filters.get("company") or company or "").strip(),
		"branch": (filters.get("branch") or branch or "").strip(),
		"cost_center": (filters.get("cost_center") or cost_center or "").strip(),
		"profit_center": (filters.get("profit_center") or profit_center or "").strip(),
		"vehicle_type": (filters.get("vehicle_type") or vehicle_type or "").strip(),
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


def _dim_clauses(filters, prefix=""):
	"""SQL conditions for company / branch / cost_center / profit_center."""
	conditions = []
	values = []
	for key in ("company", "branch", "cost_center", "profit_center"):
		val = filters.get(key)
		if not val:
			continue
		conditions.append("{0}{1} = %s".format(prefix, key))
		values.append(val)
	return conditions, values


def _vehicle_type_clause(filters, prefix=""):
	vehicle_type = filters.get("vehicle_type")
	if not vehicle_type:
		return [], []
	return ["{0}vehicle_type = %s".format(prefix)], [vehicle_type]


def _job_kpis(filters):
	"""Open / avg age / handled counts for Transport Job."""
	today = nowdate()
	from_date, to_date = _date_bounds(filters)

	dim_c, dim_v = _dim_clauses(filters)
	vt_c, vt_v = _vehicle_type_clause(filters)

	open_excludes_ph = ", ".join(["%s"] * len(OPEN_EXCLUDES))
	open_where = dim_c + vt_c + ["status NOT IN ({0})".format(open_excludes_ph)]
	open_values = dim_v + vt_v + list(OPEN_EXCLUDES)

	open_count = 0
	open_age_sum = 0
	try:
		rs = frappe.db.sql(
			"""
			SELECT COUNT(*) AS n,
			       SUM(GREATEST(DATEDIFF(%s, booking_date), 0)) AS age_sum
			FROM `tabTransport Job`
			WHERE {where}
			""".format(where=" AND ".join(open_where) or "1=1"),
			tuple([today] + open_values),
		)
		open_count = int(rs[0][0]) if rs and rs[0] and rs[0][0] is not None else 0
		open_age_sum = int(rs[0][1]) if rs and rs[0] and rs[0][1] is not None else 0
	except Exception:
		frappe.log_error(frappe.get_traceback(), "tct_open_jobs")

	handled_where = dim_c + vt_c + ["booking_date BETWEEN %s AND %s"]
	handled_values = dim_v + vt_v + [from_date, to_date]
	handled_count = 0
	try:
		rs = frappe.db.sql(
			"""
			SELECT COUNT(*) FROM `tabTransport Job`
			WHERE {where}
			""".format(where=" AND ".join(handled_where) or "1=1"),
			tuple(handled_values),
		)
		handled_count = int(rs[0][0]) if rs and rs[0] and rs[0][0] is not None else 0
	except Exception:
		frappe.log_error(frappe.get_traceback(), "tct_handled_jobs")

	avg_age = (open_age_sum / open_count) if open_count else 0.0
	return {
		"open_job_files_count": open_count,
		"avg_age_open_jobs": avg_age,
		"jobs_handled_count": handled_count,
		"by_module": [{
			"module": TRANSPORT_JOB,
			"open": open_count,
			"handled": handled_count,
			"open_avg_age": avg_age,
		}],
	}


def _avg_lead_time(filters):
	"""Average actual vs planned milestone days on Transport Jobs matching filters."""
	if not frappe.db.exists("DocType", TRANSPORT_MILESTONE):
		return 0.0

	from_date, to_date = _date_bounds(filters)
	dim_c, dim_v = _dim_clauses(filters, prefix="p.")
	vt_c, vt_v = _vehicle_type_clause(filters, prefix="p.")
	extra_parts = list(dim_c) + list(vt_c) + ["p.booking_date BETWEEN %s AND %s"]
	extra_values = list(dim_v) + list(vt_v) + [from_date, to_date]
	extra = " AND " + " AND ".join(extra_parts)

	try:
		rs = frappe.db.sql(
			"""
			SELECT
			    SUM(
			        TIMESTAMPDIFF(
			            SECOND,
			            COALESCE(c.planned_end, c.planned_start),
			            COALESCE(c.actual_end, c.actual_start)
			        )
			    ) AS sum_sec,
			    COUNT(*) AS n
			FROM `tab{child}` c
			JOIN `tab{parent}` p ON p.name = c.parent
			WHERE c.parenttype = %s
			  AND (c.actual_end IS NOT NULL OR c.actual_start IS NOT NULL)
			  AND (c.planned_end IS NOT NULL OR c.planned_start IS NOT NULL)
			  {extra}
			""".format(child=TRANSPORT_MILESTONE, parent=TRANSPORT_JOB, extra=extra),
			tuple([TRANSPORT_JOB] + extra_values),
		)
		sum_sec = flt(rs[0][0]) if rs and rs[0] and rs[0][0] is not None else 0.0
		count = int(rs[0][1]) if rs and rs[0] and rs[0][1] is not None else 0
	except Exception:
		frappe.log_error(frappe.get_traceback(), "tct_avg_lead_time")
		return 0.0

	if not count:
		return 0.0
	return (sum_sec / count) / 86400.0


def _top_vehicle_types(filters, n=DEFAULT_VEHICLE_TYPE_LIMIT):
	from_date, to_date = _date_bounds(filters)
	dim_c, dim_v = _dim_clauses(filters)
	vt_c, vt_v = _vehicle_type_clause(filters)
	conditions = dim_c + vt_c + [
		"booking_date BETWEEN %s AND %s",
		"vehicle_type IS NOT NULL",
		"vehicle_type != ''",
	]
	values = dim_v + vt_v + [from_date, to_date]
	limit = _clamp_vehicle_type_limit(n)
	try:
		rs = frappe.db.sql(
			"""
			SELECT vehicle_type AS label, COUNT(*) AS value
			FROM `tabTransport Job`
			WHERE {where}
			GROUP BY vehicle_type
			ORDER BY value DESC
			LIMIT %s
			""".format(where=" AND ".join(conditions)),
			tuple(values + [limit]),
			as_dict=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "tct_top_vehicle_types")
		rs = []
	return [{"label": r["label"], "value": flt(r["value"])} for r in rs]


def _returned_billings_count(filters):
	from_date, to_date = _date_bounds(filters)
	if not frappe.db.exists("DocType", "Returned Billing"):
		return 0

	dim_c, dim_v = _dim_clauses(filters)
	conditions = dim_c + ["returned_on BETWEEN %s AND %s"]
	values = dim_v + [from_date, to_date]
	try:
		if frappe.db.has_column("Returned Billing", "module"):
			conditions.append("(module = %s OR IFNULL(module, '') = '')")
			values.append("Transport")
	except Exception:
		pass

	vehicle_type = filters.get("vehicle_type")
	try:
		if vehicle_type:
			conditions.append(
				"""(
					IFNULL(job_no, '') != ''
					AND EXISTS (
						SELECT 1 FROM `tabTransport Job` j
						WHERE j.name = `tabReturned Billing`.job_no
						  AND j.vehicle_type = %s
					)
				)"""
			)
			values.append(vehicle_type)
		rs = frappe.db.sql(
			"SELECT COUNT(*) FROM `tabReturned Billing` WHERE {0}".format(
				" AND ".join(conditions) or "1=1"
			),
			tuple(values),
		)
		return int(rs[0][0]) if rs and rs[0] and rs[0][0] is not None else 0
	except Exception:
		frappe.log_error(frappe.get_traceback(), "tct_returned_billings")
		return 0


@frappe.whitelist()
def get_preferences():
	"""Per-user Transport Control Tower widget preferences."""
	raw = frappe.db.get_default(PREFS_KEY)
	return _merge_preferences(raw)


@frappe.whitelist()
def save_preferences(preferences=None):
	"""Persist per-user widget preferences for Transport Control Tower."""
	if isinstance(preferences, str):
		preferences = frappe.parse_json(preferences)
	merged = _merge_preferences(preferences)
	frappe.db.set_default(PREFS_KEY, frappe.as_json(merged))
	return merged


@frappe.whitelist()
def get_dashboard_data(filters=None, company=None, branch=None, cost_center=None,
		profit_center=None, vehicle_type=None, fiscal_year=None, from_date=None, to_date=None,
		vehicle_type_limit=None):
	"""Return all Transport Control Tower metrics in one call."""
	f = _parse_filters(
		filters=filters,
		company=company,
		branch=branch,
		cost_center=cost_center,
		profit_center=profit_center,
		vehicle_type=vehicle_type,
		fiscal_year=fiscal_year,
		from_date=from_date,
		to_date=to_date,
	)

	prefs = get_preferences()
	limit = _clamp_vehicle_type_limit(
		vehicle_type_limit if vehicle_type_limit not in (None, "") else prefs["vehicle_types"]["limit"]
	)

	kpi = _job_kpis(f)
	lead_time = _avg_lead_time(f)
	vehicle_types = _top_vehicle_types(f, n=limit)
	returned = _returned_billings_count(f)

	top_vehicle_types = []
	for row in vehicle_types:
		top_vehicle_types.append({
			"label": row.get("label") or _("Unknown"),
			"value": flt(row.get("value") or 0),
		})
	max_vehicle_type = max([r["value"] for r in top_vehicle_types], default=0) or 1

	return {
		"filters": f,
		"fiscal_year": f["fiscal_year"],
		"from_date": f["from_date"],
		"to_date": f["to_date"],
		"as_of": nowdate(),
		"preferences": prefs,
		"vehicle_type_limit": limit,
		"kpis": {
			"open_job_files_count": int(kpi.get("open_job_files_count") or 0),
			"avg_age_open_jobs": round(flt(kpi.get("avg_age_open_jobs") or 0), 1),
			"jobs_handled_count": int(kpi.get("jobs_handled_count") or 0),
			"avg_lead_time_per_milestone": round(flt(lead_time or 0), 1),
			"returned_billings_count": int(returned or 0),
		},
		"top_vehicle_types": top_vehicle_types,
		"top_vehicle_types_max": max_vehicle_type,
		"by_module": kpi.get("by_module") or [],
		"links": {
			"job_files_open": "TCT Job Files Detail",
			"job_files_handled": "TCT Job Files Detail",
			"milestone_lead_time": "TCT Milestone Lead Time",
			"vehicle_type_volumes": "TCT Vehicle Type Volumes",
			"returned_billings": "TCT Returned Billings",
		},
	}


@frappe.whitelist()
def get_filter_defaults():
	"""Default Company + full Company list for the dashboard filter bar."""
	companies = frappe.get_all("Company", pluck="name", order_by="name asc") or []
	company = frappe.defaults.get_user_default("Company")
	if company and company not in companies:
		companies.insert(0, company)
	if not company and companies:
		company = companies[0]
	fiscal_year = int(nowdate()[:4])
	from_date, to_date = _default_date_range(fiscal_year)
	return {
		"company": company or "",
		"companies": companies,
		"fiscal_year": fiscal_year,
		"from_date": from_date,
		"to_date": to_date,
	}


@frappe.whitelist()
def get_filter_options(company=None):
	"""Cascading Branch / Cost Center / Profit Center / Vehicle Type options."""
	company = (company or "").strip()
	branches = []
	cost_centers = []
	profit_centers = []

	if frappe.db.exists("DocType", "Branch"):
		try:
			branch_filters = {}
			if company:
				if frappe.db.has_column("Branch", "company"):
					branch_filters["company"] = company
				elif frappe.db.has_column("Branch", "custom_company"):
					branch_filters["custom_company"] = company
			branches = frappe.get_all(
				"Branch", filters=branch_filters, pluck="name", order_by="name asc"
			) or []
		except Exception:
			branches = frappe.get_all("Branch", pluck="name", order_by="name asc") or []

	if company and frappe.db.exists("DocType", "Cost Center"):
		cc_filters = {"company": company}
		if frappe.db.has_column("Cost Center", "is_group"):
			cc_filters["is_group"] = 0
		cost_centers = frappe.get_all(
			"Cost Center", filters=cc_filters, pluck="name", order_by="name asc"
		) or []

	if company and frappe.db.exists("DocType", "Profit Center"):
		profit_centers = frappe.get_all(
			"Profit Center",
			filters={"company": company} if frappe.db.has_column("Profit Center", "company") else {},
			pluck="name",
			order_by="name asc",
		) or []

	vehicle_types = []
	try:
		params = []
		where = "IFNULL(vehicle_type, '') != ''"
		if company:
			where = "company = %s AND {0}".format(where)
			params.append(company)
		rows = frappe.db.sql(
			"""
			SELECT DISTINCT vehicle_type
			FROM `tabTransport Job`
			WHERE {where}
			ORDER BY vehicle_type
			LIMIT 500
			""".format(where=where),
			tuple(params),
		)
		vehicle_types = [r[0] for r in rows if r and r[0]]
	except Exception:
		frappe.log_error(frappe.get_traceback(), "tct_vehicle_type_options")

	return {
		"company": company,
		"branches": branches,
		"cost_centers": cost_centers,
		"profit_centers": profit_centers,
		"vehicle_types": vehicle_types,
	}


_CARD_SPECS = {
	"open_job_files_count": {
		"report": "TCT Job Files Detail",
		"fieldtype": "Int",
		"extra": {"scope": "Open"},
	},
	"avg_age_open_jobs": {
		"report": "TCT Job Files Detail",
		"fieldtype": "Float",
		"extra": {"scope": "Open"},
	},
	"jobs_handled_count": {
		"report": "TCT Job Files Detail",
		"fieldtype": "Int",
		"extra": {"scope": "Handled"},
	},
	"avg_lead_time_per_milestone": {
		"report": "TCT Milestone Lead Time",
		"fieldtype": "Float",
		"extra": {},
	},
	"returned_billings_count": {
		"report": "TCT Returned Billings",
		"fieldtype": "Int",
		"extra": {},
	},
}


def _card_filters(filters):
	"""Split the Number Card metric out of the filter payload."""
	if isinstance(filters, str):
		filters = frappe.parse_json(filters) or {}
	if not isinstance(filters, dict):
		filters = {}
	filters = dict(filters)
	metric = (filters.pop("metric", None) or "").strip()
	if not (filters.get("company") or "").strip():
		filters["company"] = frappe.defaults.get_user_default("Company") or ""
	return metric, filters


def _route_options(parsed, extra=None):
	options = {
		"fiscal_year": parsed.get("fiscal_year"),
		"from_date": parsed.get("from_date"),
		"to_date": parsed.get("to_date"),
	}
	if parsed.get("company"):
		options["company"] = parsed.get("company")
	for key in ("branch", "cost_center", "profit_center", "vehicle_type"):
		if parsed.get(key):
			options[key] = parsed.get(key)
	options.update(extra or {})
	return options


def module_snapshot_rows(filters=None):
	"""Module, open, average age, and handled rows for the snapshot chart."""
	parsed = _parse_filters(filters)
	rows = []
	for row in _job_kpis(parsed).get("by_module") or []:
		rows.append({
			"module": row.get("module") or TRANSPORT_JOB,
			"open": int(row.get("open") or 0),
			"open_avg_age": round(flt(row.get("open_avg_age") or 0), 1),
			"handled": int(row.get("handled") or 0),
		})
	return rows


@frappe.whitelist()
def number_card_value(filters=None):
	"""Custom Number Card value for the Transport Control Tower dashboard.

	``filters.metric`` selects the KPI. Clicking the card opens the matching
	detail report with the same company and date range.
	"""
	metric, raw = _card_filters(filters)
	spec = _CARD_SPECS.get(metric)
	if not spec:
		return {"value": 0, "fieldtype": "Int"}

	parsed = _parse_filters(raw)
	if metric in ("open_job_files_count", "avg_age_open_jobs", "jobs_handled_count"):
		value = (_job_kpis(parsed) or {}).get(metric) or 0
	elif metric == "avg_lead_time_per_milestone":
		value = _avg_lead_time(parsed)
	else:
		value = _returned_billings_count(parsed)

	if spec["fieldtype"] == "Int":
		value = int(value or 0)
	else:
		value = round(flt(value or 0), 1)

	return {
		"value": value,
		"fieldtype": spec["fieldtype"],
		"route": ["query-report", spec["report"]],
		"route_options": _route_options(parsed, spec.get("extra")),
	}
