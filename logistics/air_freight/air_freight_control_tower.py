# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Air Freight Control Tower dashboard API.

Aggregates air-freight operational KPIs for the ``air-freight-control-tower``
desk page, filtered by Company / Branch / Cost Center / Profit Center / UNLOCO:

- Number of open job files
- Average age of open job files
- Number of job files handled (YTD)
- Average lead time per milestone
- Top airlines (limit is a per-user preference)
- Number of returned billings (YTD)
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

OPEN_EXCLUDES = ("Completed", "Closed", "Cancelled")
AIR_SHIPMENT = "Air Shipment"
AIR_MILESTONE = "Air Shipment Milestone"
PREFS_KEY = "afct_preferences"
DEFAULT_AIRLINE_LIMIT = 10
MAX_AIRLINE_LIMIT = 50

DEFAULT_PREFERENCES = {
	"kpis": {
		"show_open_jobs": 1,
		"show_avg_age": 1,
		"show_handled": 1,
		"show_lead_time": 1,
		"warn_age_days": 60,
	},
	"airlines": {
		"limit": DEFAULT_AIRLINE_LIMIT,
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


def _clamp_airline_limit(n):
	n = cint(n) or DEFAULT_AIRLINE_LIMIT
	return max(1, min(MAX_AIRLINE_LIMIT, n))


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
	out["airlines"]["limit"] = _clamp_airline_limit(out["airlines"].get("limit"))
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
		profit_center=None, unloco=None, fiscal_year=None, from_date=None, to_date=None):
	"""Normalize whitelist args into a filter dict.

	Accepts either a JSON ``filters`` object or individual kwargs (desk call).
	"""
	if isinstance(filters, str):
		filters = frappe.parse_json(filters) or {}
	if not isinstance(filters, dict):
		filters = {}

	out = {
		"company": (filters.get("company") or company or "").strip(),
		"branch": (filters.get("branch") or branch or "").strip(),
		"cost_center": (filters.get("cost_center") or cost_center or "").strip(),
		"profit_center": (filters.get("profit_center") or profit_center or "").strip(),
		"unloco": (filters.get("unloco") or unloco or "").strip(),
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


def _unloco_clause(filters, prefix=""):
	"""Match origin_port or destination_port when UNLOCO is set."""
	unloco = filters.get("unloco")
	if not unloco:
		return [], []
	return (
		["({0}origin_port = %s OR {0}destination_port = %s)".format(prefix)],
		[unloco, unloco],
	)


def _air_shipment_kpis(filters):
	"""Open / avg age / handled counts for Air Shipment."""
	today = nowdate()
	from_date, to_date = _date_bounds(filters)

	dim_c, dim_v = _dim_clauses(filters)
	unloco_c, unloco_v = _unloco_clause(filters)

	open_excludes_ph = ", ".join(["%s"] * len(OPEN_EXCLUDES))
	open_where = dim_c + unloco_c + ["job_status NOT IN ({0})".format(open_excludes_ph)]
	open_values = dim_v + unloco_v + list(OPEN_EXCLUDES)

	open_count = 0
	open_age_sum = 0
	try:
		rs = frappe.db.sql(
			"""
			SELECT COUNT(*) AS n,
			       SUM(GREATEST(DATEDIFF(%s, booking_date), 0)) AS age_sum
			FROM `tabAir Shipment`
			WHERE {where}
			""".format(where=" AND ".join(open_where) or "1=1"),
			tuple([today] + open_values),
		)
		open_count = int(rs[0][0]) if rs and rs[0] and rs[0][0] is not None else 0
		open_age_sum = int(rs[0][1]) if rs and rs[0] and rs[0][1] is not None else 0
	except Exception:
		frappe.log_error(frappe.get_traceback(), "afct_open_jobs")

	handled_where = dim_c + unloco_c + ["booking_date BETWEEN %s AND %s"]
	handled_values = dim_v + unloco_v + [from_date, to_date]
	handled_count = 0
	try:
		rs = frappe.db.sql(
			"""
			SELECT COUNT(*) FROM `tabAir Shipment`
			WHERE {where}
			""".format(where=" AND ".join(handled_where) or "1=1"),
			tuple(handled_values),
		)
		handled_count = int(rs[0][0]) if rs and rs[0] and rs[0][0] is not None else 0
	except Exception:
		frappe.log_error(frappe.get_traceback(), "afct_handled_jobs")

	avg_age = (open_age_sum / open_count) if open_count else 0.0
	return {
		"open_job_files_count": open_count,
		"avg_age_open_jobs": avg_age,
		"jobs_handled_count": handled_count,
		"by_module": [{
			"module": AIR_SHIPMENT,
			"open": open_count,
			"handled": handled_count,
			"open_avg_age": avg_age,
		}],
	}


def _avg_lead_time(filters):
	"""Average actual vs planned milestone days on Air Shipments matching filters."""
	if not frappe.db.exists("DocType", AIR_MILESTONE):
		return 0.0

	from_date, to_date = _date_bounds(filters)
	dim_c, dim_v = _dim_clauses(filters, prefix="p.")
	unloco_c, unloco_v = _unloco_clause(filters, prefix="p.")
	extra_parts = list(dim_c) + list(unloco_c) + ["p.booking_date BETWEEN %s AND %s"]
	extra_values = list(dim_v) + list(unloco_v) + [from_date, to_date]
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
			""".format(child=AIR_MILESTONE, parent=AIR_SHIPMENT, extra=extra),
			tuple([AIR_SHIPMENT] + extra_values),
		)
		sum_sec = flt(rs[0][0]) if rs and rs[0] and rs[0][0] is not None else 0.0
		count = int(rs[0][1]) if rs and rs[0] and rs[0][1] is not None else 0
	except Exception:
		frappe.log_error(frappe.get_traceback(), "afct_avg_lead_time")
		return 0.0

	if not count:
		return 0.0
	return (sum_sec / count) / 86400.0


def _top_airlines(filters, n=DEFAULT_AIRLINE_LIMIT):
	from_date, to_date = _date_bounds(filters)
	dim_c, dim_v = _dim_clauses(filters)
	unloco_c, unloco_v = _unloco_clause(filters)
	conditions = dim_c + unloco_c + [
		"booking_date BETWEEN %s AND %s",
		"airline IS NOT NULL",
		"airline != ''",
	]
	values = dim_v + unloco_v + [from_date, to_date]
	limit = _clamp_airline_limit(n)
	try:
		rs = frappe.db.sql(
			"""
			SELECT airline AS label, COUNT(*) AS value
			FROM `tabAir Shipment`
			WHERE {where}
			GROUP BY airline
			ORDER BY value DESC
			LIMIT %s
			""".format(where=" AND ".join(conditions)),
			tuple(values + [limit]),
			as_dict=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "afct_top_airlines")
		rs = []
	return [{"label": r["label"], "value": flt(r["value"])} for r in rs]


def _returned_billings_count(filters):
	from_date, to_date = _date_bounds(filters)
	if not frappe.db.exists("DocType", "Returned Billing"):
		return 0

	dim_c, dim_v = _dim_clauses(filters)
	conditions = dim_c + ["returned_on BETWEEN %s AND %s"]
	values = dim_v + [from_date, to_date]
	# Prefer Air Freight module rows when the column exists.
	try:
		if frappe.db.has_column("Returned Billing", "module"):
			conditions.append("(module = %s OR IFNULL(module, '') = '')")
			values.append("Air Freight")
	except Exception:
		pass

	# UNLOCO is not on Returned Billing — when set, restrict via linked Air Shipment.
	unloco = filters.get("unloco")
	try:
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
		rs = frappe.db.sql(
			"SELECT COUNT(*) FROM `tabReturned Billing` WHERE {0}".format(
				" AND ".join(conditions) or "1=1"
			),
			tuple(values),
		)
		return int(rs[0][0]) if rs and rs[0] and rs[0][0] is not None else 0
	except Exception:
		frappe.log_error(frappe.get_traceback(), "afct_returned_billings")
		return 0


@frappe.whitelist()
def get_preferences():
	"""Per-user Air Freight Control Tower widget preferences."""
	raw = frappe.db.get_default(PREFS_KEY)
	return _merge_preferences(raw)


@frappe.whitelist()
def save_preferences(preferences=None):
	"""Persist per-user widget preferences for Air Freight Control Tower."""
	if isinstance(preferences, str):
		preferences = frappe.parse_json(preferences)
	merged = _merge_preferences(preferences)
	frappe.db.set_default(PREFS_KEY, frappe.as_json(merged))
	return merged


@frappe.whitelist()
def get_dashboard_data(filters=None, company=None, branch=None, cost_center=None,
		profit_center=None, unloco=None, fiscal_year=None, from_date=None, to_date=None,
		airline_limit=None):
	"""Return all Air Freight Control Tower metrics in one call."""
	f = _parse_filters(
		filters=filters,
		company=company,
		branch=branch,
		cost_center=cost_center,
		profit_center=profit_center,
		unloco=unloco,
		fiscal_year=fiscal_year,
		from_date=from_date,
		to_date=to_date,
	)

	prefs = get_preferences()
	limit = _clamp_airline_limit(
		airline_limit if airline_limit not in (None, "") else prefs["airlines"]["limit"]
	)

	kpi = _air_shipment_kpis(f)
	lead_time = _avg_lead_time(f)
	airlines = _top_airlines(f, n=limit)
	returned = _returned_billings_count(f)

	top_airlines = []
	for row in airlines:
		top_airlines.append({
			"label": row.get("label") or _("Unknown"),
			"value": flt(row.get("value") or 0),
		})
	max_airline = max([r["value"] for r in top_airlines], default=0) or 1

	return {
		"filters": f,
		"fiscal_year": f["fiscal_year"],
		"from_date": f["from_date"],
		"to_date": f["to_date"],
		"as_of": nowdate(),
		"preferences": prefs,
		"airline_limit": limit,
		"kpis": {
			"open_job_files_count": int(kpi.get("open_job_files_count") or 0),
			"avg_age_open_jobs": round(flt(kpi.get("avg_age_open_jobs") or 0), 1),
			"jobs_handled_count": int(kpi.get("jobs_handled_count") or 0),
			"avg_lead_time_per_milestone": round(flt(lead_time or 0), 1),
			"returned_billings_count": int(returned or 0),
		},
		"top_airlines": top_airlines,
		"top_airlines_max": max_airline,
		"by_module": kpi.get("by_module") or [],
		"links": {
			"job_files_open": "AFCT Job Files Detail",
			"job_files_handled": "AFCT Job Files Detail",
			"milestone_lead_time": "AFCT Milestone Lead Time",
			"airline_volumes": "AFCT Airline Volumes",
			"returned_billings": "AFCT Returned Billings",
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
	"""Cascading Branch / Cost Center / Profit Center / UNLOCO options.

	UNLOCO options are distinct origin/destination ports used on Air Shipments
	(optionally scoped by company) so the dropdown stays usable.
	"""
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

	unloco_values = []
	try:
		params = []
		where = "IFNULL(origin_port, '') != '' OR IFNULL(destination_port, '') != ''"
		if company:
			where = "company = %s AND ({0})".format(where)
			params.append(company)
		rows = frappe.db.sql(
			"""
			SELECT DISTINCT port FROM (
				SELECT origin_port AS port FROM `tabAir Shipment` WHERE {where}
				UNION
				SELECT destination_port AS port FROM `tabAir Shipment` WHERE {where}
			) u
			WHERE IFNULL(port, '') != ''
			ORDER BY port
			LIMIT 500
			""".format(where=where),
			tuple(params + params),
		)
		unloco_values = [r[0] for r in rows if r and r[0]]
	except Exception:
		frappe.log_error(frappe.get_traceback(), "afct_unloco_options")

	return {
		"company": company,
		"branches": branches,
		"cost_centers": cost_centers,
		"profit_centers": profit_centers,
		"unlocos": unloco_values,
	}
