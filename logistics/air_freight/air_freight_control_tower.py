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
- Top 5 airlines
- Number of returned billings (YTD)
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint, flt, nowdate

OPEN_EXCLUDES = ("Completed", "Closed", "Cancelled")
AIR_SHIPMENT = "Air Shipment"
AIR_MILESTONE = "Air Shipment Milestone"


def _parse_filters(filters=None, company=None, branch=None, cost_center=None,
		profit_center=None, unloco=None, fiscal_year=None):
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
	year = filters["fiscal_year"]
	year_start = "{0}-01-01".format(year)
	year_end = "{0}-12-31".format(year)

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
	handled_values = dim_v + unloco_v + [year_start, year_end]
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

	dim_c, dim_v = _dim_clauses(filters, prefix="p.")
	unloco_c, unloco_v = _unloco_clause(filters, prefix="p.")
	extra = ""
	if dim_c or unloco_c:
		extra = " AND " + " AND ".join(dim_c + unloco_c)

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
			tuple([AIR_SHIPMENT] + dim_v + unloco_v),
		)
		sum_sec = flt(rs[0][0]) if rs and rs[0] and rs[0][0] is not None else 0.0
		count = int(rs[0][1]) if rs and rs[0] and rs[0][1] is not None else 0
	except Exception:
		frappe.log_error(frappe.get_traceback(), "afct_avg_lead_time")
		return 0.0

	if not count:
		return 0.0
	return (sum_sec / count) / 86400.0


def _top_airlines(filters, n=5):
	year = filters["fiscal_year"]
	year_start = "{0}-01-01".format(year)
	year_end = "{0}-12-31".format(year)
	dim_c, dim_v = _dim_clauses(filters)
	unloco_c, unloco_v = _unloco_clause(filters)
	conditions = dim_c + unloco_c + [
		"booking_date BETWEEN %s AND %s",
		"airline IS NOT NULL",
		"airline != ''",
	]
	values = dim_v + unloco_v + [year_start, year_end]
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
			tuple(values + [cint(n)]),
			as_dict=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "afct_top_airlines")
		rs = []
	return [{"label": r["label"], "value": flt(r["value"])} for r in rs]


def _returned_billings_count(filters):
	year = filters["fiscal_year"]
	year_start = "{0}-01-01".format(year)
	year_end = "{0}-12-31".format(year)
	if not frappe.db.exists("DocType", "Returned Billing"):
		return 0

	dim_c, dim_v = _dim_clauses(filters)
	conditions = dim_c + ["returned_on BETWEEN %s AND %s"]
	values = dim_v + [year_start, year_end]
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
def get_dashboard_data(filters=None, company=None, branch=None, cost_center=None,
		profit_center=None, unloco=None, fiscal_year=None):
	"""Return all Air Freight Control Tower metrics in one call."""
	f = _parse_filters(
		filters=filters,
		company=company,
		branch=branch,
		cost_center=cost_center,
		profit_center=profit_center,
		unloco=unloco,
		fiscal_year=fiscal_year,
	)

	kpi = _air_shipment_kpis(f)
	lead_time = _avg_lead_time(f)
	airlines = _top_airlines(f, n=5)
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
		"as_of": nowdate(),
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
			"control_tower_dashboard": "Control Tower - ATN Airfreight",
			"jobs_report": "CT Jobs KPI",
			"airlines_report": "CT Top Carriers Volumes",
			"returned_billings_report": "CT Returned Billings",
		},
	}


@frappe.whitelist()
def get_filter_defaults():
	"""Default Company for the dashboard filter bar."""
	company = frappe.defaults.get_user_default("Company")
	if not company:
		companies = frappe.get_all("Company", pluck="name", limit=1, order_by="name asc")
		company = companies[0] if companies else ""
	return {
		"company": company or "",
		"fiscal_year": int(nowdate()[:4]),
	}
