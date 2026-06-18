# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
"""Control Tower aggregation API.

Cross-module rollup helpers used by all Control Tower charts, number cards,
and Script Reports. Every function takes an organization name (``Control
Tower Organization`` primary key) and resolves the underlying ``company /
branch / cost_center / profit_center`` filter set from the org's mapping
rows.

Design rules:
- Pure read-only queries; no writes.
- Whitelisted helpers are safe for unauthenticated dashboard chart polling
  inside the desk (``frappe.whitelist()``).
- Currency is always reported in PHP; cross-currency revenue/cost is summed
  at booked values without FX conversion (matches existing reports in the
  app).
"""

from __future__ import unicode_literals

import json
from collections import defaultdict

import frappe
from frappe.utils import flt, nowdate


# Source job DocTypes used by GP and operations rollups.
# Tuple shape: (doctype, date_field, status_field, open_excludes)
JOB_SOURCES = [
	("Sea Shipment", "booking_date", "job_status", ("Completed", "Closed", "Cancelled")),
	("Air Shipment", "booking_date", "job_status", ("Completed", "Closed", "Cancelled")),
	("Transport Job", "booking_date", "status", ("Completed", "Closed", "Cancelled")),
	("Declaration", "declaration_date", "job_status", ("Completed", "Closed", "Cancelled")),
	("Warehouse Job", "job_open_date", "job_status", ("Completed", "Closed", "Cancelled")),
	("Project Job", "creation", "status", ("Completed", "Closed", "Cancelled")),
	("Exhibit Job", "creation", "status", ("Completed", "Closed", "Cancelled")),
	("MICE Job", "creation", "status", ("Completed", "Closed", "Cancelled")),
]

# Lead-time milestone child tables. (child_doctype, parent_doctype).
MILESTONE_SOURCES = [
	("Sea Shipment Milestone", "Sea Shipment"),
	("Sea Booking Milestone", "Sea Booking"),
	("Air Shipment Milestone", "Air Shipment"),
	("Air Booking Milestone", "Air Booking"),
	("Transport Job Milestone", "Transport Job"),
	("Transport Order Milestone", "Transport Order"),
	("Declaration Milestone", "Declaration"),
	("Declaration Order Milestone", "Declaration Order"),
	("Special Project Milestone", "Special Project"),
	("MICE Project Milestone", "MICE Project"),
	("Exhibit Milestone", "Exhibit"),
]

GP_EXPR_ESTIMATED = "(COALESCE(estimated_revenue,0) - COALESCE(estimated_costs,0))"
GP_EXPR_RECOGNIZED = "(COALESCE(recognized_revenue,0) - COALESCE(recognized_costs,0))"

# TEU derivation from Sea Freight Containers.size (typically "20" / "40" / "45" ft strings).
TEU_CASE = (
	"CASE "
	"WHEN c.size LIKE '20%%' THEN 1 "
	"WHEN c.size LIKE '40%%' THEN 2 "
	"WHEN c.size LIKE '45%%' THEN 2 "
	"ELSE 1 END"
)


# ----------------------------------------------------------------------------- #
# Filter resolution                                                             #
# ----------------------------------------------------------------------------- #


@frappe.whitelist()
def resolve_org_filters(organization):
	"""Return the dimension-filter dict for an organization.

	``{"company": [...], "branch": [...], "cost_center": [...],
	"profit_center": [...]}``. Empty list = wildcard.
	"""
	if not organization:
		return {"company": [], "branch": [], "cost_center": [], "profit_center": []}
	rows = frappe.get_all(
		"Control Tower Org Mapping",
		filters={"parenttype": "Control Tower Organization", "parent": organization},
		fields=["company", "branch", "cost_center", "profit_center"],
	)
	bucket = {"company": set(), "branch": set(), "cost_center": set(), "profit_center": set()}
	for r in rows:
		for key in bucket:
			v = r.get(key)
			if v:
				bucket[key].add(v)
	return {k: sorted(v) for k, v in bucket.items()}


def _dim_clauses(filters, prefix=""):
	"""Build SQL fragments + values for a filter dict.

	Returns ``(list_of_sql_conditions, list_of_values)``. Empty lists when
	filters is empty / wildcard.
	"""
	conditions = []
	values = []
	if not filters:
		return conditions, values
	for key in ("company", "branch", "cost_center", "profit_center"):
		vals = filters.get(key) or []
		if not vals:
			continue
		placeholders = ", ".join(["%s"] * len(vals))
		conditions.append("{0}{1} IN ({2})".format(prefix, key, placeholders))
		values.extend(vals)
	return conditions, values


# ----------------------------------------------------------------------------- #
# GP summary                                                                    #
# ----------------------------------------------------------------------------- #


@frappe.whitelist()
def get_gp_summary(organization, fiscal_year=None, currency="PHP"):
	"""GP YTD / Prior YTD / Target / % vs target + 3-year breakdown.

	GP = estimated_revenue - estimated_costs, summed across the 8 job sources.
	"""
	year = int(fiscal_year) if fiscal_year else int(nowdate()[:4])
	filters = resolve_org_filters(organization)

	def _gp_for_year(y):
		total = 0.0
		for (doctype, date_field, _sf, _oe) in JOB_SOURCES:
			if not frappe.db.exists("DocType", doctype):
				continue
			conditions = ["{0} BETWEEN %s AND %s".format(date_field)]
			values = ["{0}-01-01".format(y), "{0}-12-31".format(y)]
			dim_conditions, dim_values = _dim_clauses(filters)
			conditions.extend(dim_conditions)
			values.extend(dim_values)
			where = " AND ".join(conditions)
			try:
				rs = frappe.db.sql(
					"SELECT SUM({gp}) FROM `tab{dt}` WHERE {where}".format(
						gp=GP_EXPR_ESTIMATED, dt=doctype, where=where
					),
					tuple(values),
				)
				total += flt(rs[0][0]) if rs and rs[0] and rs[0][0] is not None else 0.0
			except Exception:
				frappe.log_error(frappe.get_traceback(), "ct_gp_summary {0}".format(doctype))
		return total

	gp_current = _gp_for_year(year)
	gp_prior = _gp_for_year(year - 1)
	gp_prior_prior = _gp_for_year(year - 2)

	target = flt(
		frappe.db.get_value(
			"Control Tower GP Target",
			{"organization": organization, "fiscal_year": str(year)},
			"target_amount",
		)
		or 0
	)
	pct = (gp_current / target * 100.0) if target else 0.0

	return {
		"organization": organization,
		"fiscal_year": year,
		"currency": currency,
		"gp_ytd": gp_current,
		"gp_prior_ytd": gp_prior,
		"gp_prior_prior_ytd": gp_prior_prior,
		"gp_target": target,
		"gp_vs_target_pct": pct,
		"breakdown": [
			{"year": year - 2, "gp": gp_prior_prior},
			{"year": year - 1, "gp": gp_prior},
			{"year": year, "gp": gp_current},
		],
	}


# ----------------------------------------------------------------------------- #
# Jobs KPI (Open / Avg Age / Handled / Avg Lead Time / Returned Billings)       #
# ----------------------------------------------------------------------------- #


@frappe.whitelist()
def get_jobs_kpi(organization, modules=None, fiscal_year=None):
	"""Cost Center operational KPIs for an organization."""
	filters = resolve_org_filters(organization)
	year = int(fiscal_year) if fiscal_year else int(nowdate()[:4])
	year_start = "{0}-01-01".format(year)
	year_end = "{0}-12-31".format(year)
	today = nowdate()
	if isinstance(modules, str):
		try:
			modules = json.loads(modules)
		except Exception:
			modules = [m.strip() for m in modules.split(",") if m.strip()]

	open_count = 0
	open_age_sum = 0
	handled_count = 0
	by_module = []

	for (doctype, date_field, status_field, open_excludes) in JOB_SOURCES:
		if modules and doctype not in modules:
			continue
		if not frappe.db.exists("DocType", doctype):
			continue
		dim_conditions, dim_values = _dim_clauses(filters)

		open_excludes_ph = ", ".join(["%s"] * len(open_excludes))
		open_where = dim_conditions + ["{0} NOT IN ({1})".format(status_field, open_excludes_ph)]
		open_values = dim_values + list(open_excludes)
		try:
			rs = frappe.db.sql(
				"""
				SELECT COUNT(*) AS n,
				       SUM(GREATEST(DATEDIFF(%s, {df}), 0)) AS age_sum
				FROM `tab{dt}`
				WHERE {where}
				""".format(df=date_field, dt=doctype, where=" AND ".join(open_where) or "1=1"),
				tuple([today] + open_values),
			)
			n = int(rs[0][0]) if rs and rs[0] and rs[0][0] is not None else 0
			age = int(rs[0][1]) if rs and rs[0] and rs[0][1] is not None else 0
		except Exception:
			frappe.log_error(frappe.get_traceback(), "ct_jobs_kpi open {0}".format(doctype))
			n, age = 0, 0
		open_count += n
		open_age_sum += age

		handled_where = dim_conditions + ["{0} BETWEEN %s AND %s".format(date_field)]
		handled_values = dim_values + [year_start, year_end]
		try:
			rs = frappe.db.sql(
				"""
				SELECT COUNT(*) FROM `tab{dt}` WHERE {where}
				""".format(dt=doctype, where=" AND ".join(handled_where) or "1=1"),
				tuple(handled_values),
			)
			h = int(rs[0][0]) if rs and rs[0] and rs[0][0] is not None else 0
		except Exception:
			frappe.log_error(frappe.get_traceback(), "ct_jobs_kpi handled {0}".format(doctype))
			h = 0
		handled_count += h
		by_module.append({"module": doctype, "open": n, "handled": h, "open_avg_age": (age / n) if n else 0})

	avg_age = (open_age_sum / open_count) if open_count else 0
	lead_time = get_avg_lead_time(organization)
	returned_billings_count = _returned_billings_count(filters, year_start, year_end)

	return {
		"organization": organization,
		"fiscal_year": year,
		"open_job_files_count": open_count,
		"avg_age_open_jobs": avg_age,
		"jobs_handled_count": handled_count,
		"avg_lead_time_per_milestone": lead_time,
		"returned_billings_count": returned_billings_count,
		"by_module": by_module,
	}


def _returned_billings_count(filters, date_from, date_to):
	conditions = ["returned_on BETWEEN %s AND %s"]
	values = [date_from, date_to]
	dim_conditions, dim_values = _dim_clauses(filters)
	conditions.extend(dim_conditions)
	values.extend(dim_values)
	try:
		rs = frappe.db.sql(
			"SELECT COUNT(*) FROM `tabReturned Billing` WHERE {0}".format(" AND ".join(conditions)),
			tuple(values),
		)
		return int(rs[0][0]) if rs and rs[0] and rs[0][0] is not None else 0
	except Exception:
		frappe.log_error(frappe.get_traceback(), "ct_returned_billings_count")
		return 0


# ----------------------------------------------------------------------------- #
# Lead time per milestone                                                       #
# ----------------------------------------------------------------------------- #


@frappe.whitelist()
def get_avg_lead_time(organization):
	"""Average ``actual_end - planned_end`` (days) across all milestone child
	rows for parent jobs in the org. Falls back to ``actual_start - planned_start``
	when ``actual_end`` is null.
	"""
	filters = resolve_org_filters(organization)
	dim_conditions, dim_values = _dim_clauses(filters, prefix="p.")
	dim_where = (" AND " + " AND ".join(dim_conditions)) if dim_conditions else ""
	sum_seconds = 0.0
	count = 0
	for child, parent in MILESTONE_SOURCES:
		# Skip silently when the milestone child or its parent DocType is
		# not installed on this tenant (e.g. Exhibit / MICE legacy split).
		if not frappe.db.exists("DocType", child) or not frappe.db.exists("DocType", parent):
			continue
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
				  {dim_where}
				""".format(child=child, parent=parent, dim_where=dim_where),
				tuple([parent] + dim_values),
			)
			ss = flt(rs[0][0]) if rs and rs[0] and rs[0][0] is not None else 0.0
			n = int(rs[0][1]) if rs and rs[0] and rs[0][1] is not None else 0
		except Exception:
			frappe.log_error(frappe.get_traceback(), "ct_avg_lead_time {0}".format(child))
			ss, n = 0.0, 0
		sum_seconds += ss
		count += n
	if not count:
		return 0.0
	return (sum_seconds / count) / 86400.0


# ----------------------------------------------------------------------------- #
# Top N rankings                                                                #
# ----------------------------------------------------------------------------- #


@frappe.whitelist()
def get_top_n(organization, dimension, n=10, fiscal_year=None):
	"""Generic top-N rollup. Supported dimensions (each returns
	``[{label, value}]`` sorted DESC):

	- ``customer`` (GP across all 8 job sources)
	- ``carrier_sea_fcl_teu`` (Sea Shipment containers, TEU sum)
	- ``carrier_sea_lcl_cbm`` (Sea Shipment packages, CBM sum, FCL filtered out)
	- ``carrier_air_chw`` (Air Shipment chargeable weight)
	- ``airline`` (Air Shipment count by airline)
	- ``agent_sea_fcl_teu`` / ``agent_sea_lcl_cbm`` / ``agent_air_chw`` (Freight Agent)
	- ``outsourced_trucker`` (Transport Job count grouped by supplier)
	- ``outsourced_broker`` (Declaration count grouped by broker)
	- ``supplier`` (Purchase Invoice supplier total)
	"""
	n = int(n or 10)
	year = int(fiscal_year) if fiscal_year else int(nowdate()[:4])
	year_start = "{0}-01-01".format(year)
	year_end = "{0}-12-31".format(year)
	filters = resolve_org_filters(organization)

	dispatchers = {
		"customer": lambda: _top_customers_by_gp(filters, n, year_start, year_end),
		"carrier_sea_fcl_teu": lambda: _top_sea_by_teu(filters, "shipping_line", n, year_start, year_end),
		"carrier_sea_lcl_cbm": lambda: _top_sea_by_cbm(filters, "shipping_line", n, year_start, year_end),
		"carrier_air_chw": lambda: _top_air_by_chw(filters, "airline", n, year_start, year_end),
		"airline": lambda: _top_air_count(filters, "airline", n, year_start, year_end),
		"agent_sea_fcl_teu": lambda: _top_sea_by_teu(filters, "freight_agent", n, year_start, year_end),
		"agent_sea_lcl_cbm": lambda: _top_sea_by_cbm(filters, "freight_agent", n, year_start, year_end),
		"agent_air_chw": lambda: _top_air_by_chw(filters, "freight_agent", n, year_start, year_end),
		"outsourced_trucker": lambda: _top_outsourced(filters, "Transport Job", "booking_date", "ct_outsourced_to_supplier", n, year_start, year_end),
		"outsourced_broker": lambda: _top_outsourced(filters, "Declaration", "declaration_date", "ct_outsourced_to_broker", n, year_start, year_end),
		"supplier": lambda: _top_suppliers(filters, n, year_start, year_end),
	}
	if dimension not in dispatchers:
		frappe.throw("Unknown top-N dimension: {0}".format(dimension))
	return dispatchers[dimension]()


def _top_customers_by_gp(filters, n, year_start, year_end):
	bucket = defaultdict(float)
	for (doctype, date_field, _sf, _oe) in JOB_SOURCES:
		if not frappe.db.exists("DocType", doctype):
			continue
		conditions = ["{0} BETWEEN %s AND %s".format(date_field), "customer IS NOT NULL", "customer != ''"]
		values = [year_start, year_end]
		dim_conditions, dim_values = _dim_clauses(filters)
		conditions.extend(dim_conditions)
		values.extend(dim_values)
		try:
			rs = frappe.db.sql(
				"""
				SELECT customer AS label, SUM({gp}) AS value
				FROM `tab{dt}`
				WHERE {where}
				GROUP BY customer
				""".format(gp=GP_EXPR_ESTIMATED, dt=doctype, where=" AND ".join(conditions)),
				tuple(values),
				as_dict=True,
			)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "ct_top_customers_by_gp {0}".format(doctype))
			rs = []
		for r in rs:
			bucket[r["label"]] += flt(r["value"])
	ranked = sorted(bucket.items(), key=lambda kv: kv[1], reverse=True)[:n]
	return [{"label": k, "value": v} for k, v in ranked]


def _top_sea_by_teu(filters, group_field, n, year_start, year_end):
	conditions = ["s.booking_date BETWEEN %s AND %s", "s.{0} IS NOT NULL".format(group_field), "s.{0} != ''".format(group_field)]
	values = [year_start, year_end]
	dim_conditions, dim_values = _dim_clauses(filters, prefix="s.")
	conditions.extend(dim_conditions)
	values.extend(dim_values)
	try:
		rs = frappe.db.sql(
			"""
			SELECT s.{gf} AS label, SUM({teu}) AS value
			FROM `tabSea Shipment` s
			JOIN `tabSea Freight Containers` c ON c.parent = s.name AND c.parenttype = 'Sea Shipment'
			WHERE {where}
			GROUP BY s.{gf}
			ORDER BY value DESC
			LIMIT %s
			""".format(gf=group_field, teu=TEU_CASE, where=" AND ".join(conditions)),
			tuple(values + [n]),
			as_dict=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "ct_top_sea_by_teu {0}".format(group_field))
		rs = []
	return [{"label": r["label"], "value": flt(r["value"])} for r in rs]


def _top_sea_by_cbm(filters, group_field, n, year_start, year_end):
	conditions = [
		"s.booking_date BETWEEN %s AND %s",
		"s.{0} IS NOT NULL".format(group_field),
		"s.{0} != ''".format(group_field),
		"(p.container IS NULL OR p.container = '')",  # LCL filter: no container assignment
	]
	values = [year_start, year_end]
	dim_conditions, dim_values = _dim_clauses(filters, prefix="s.")
	conditions.extend(dim_conditions)
	values.extend(dim_values)
	try:
		rs = frappe.db.sql(
			"""
			SELECT s.{gf} AS label, SUM(COALESCE(p.volume, 0)) AS value
			FROM `tabSea Shipment` s
			JOIN `tabSea Freight Packages` p ON p.parent = s.name AND p.parenttype = 'Sea Shipment'
			WHERE {where}
			GROUP BY s.{gf}
			ORDER BY value DESC
			LIMIT %s
			""".format(gf=group_field, where=" AND ".join(conditions)),
			tuple(values + [n]),
			as_dict=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "ct_top_sea_by_cbm {0}".format(group_field))
		rs = []
	return [{"label": r["label"], "value": flt(r["value"])} for r in rs]


def _top_air_by_chw(filters, group_field, n, year_start, year_end):
	conditions = ["booking_date BETWEEN %s AND %s", "{0} IS NOT NULL".format(group_field), "{0} != ''".format(group_field)]
	values = [year_start, year_end]
	dim_conditions, dim_values = _dim_clauses(filters)
	conditions.extend(dim_conditions)
	values.extend(dim_values)
	try:
		rs = frappe.db.sql(
			"""
			SELECT {gf} AS label, SUM(COALESCE(chargeable, 0)) AS value
			FROM `tabAir Shipment`
			WHERE {where}
			GROUP BY {gf}
			ORDER BY value DESC
			LIMIT %s
			""".format(gf=group_field, where=" AND ".join(conditions)),
			tuple(values + [n]),
			as_dict=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "ct_top_air_by_chw {0}".format(group_field))
		rs = []
	return [{"label": r["label"], "value": flt(r["value"])} for r in rs]


def _top_air_count(filters, group_field, n, year_start, year_end):
	conditions = ["booking_date BETWEEN %s AND %s", "{0} IS NOT NULL".format(group_field), "{0} != ''".format(group_field)]
	values = [year_start, year_end]
	dim_conditions, dim_values = _dim_clauses(filters)
	conditions.extend(dim_conditions)
	values.extend(dim_values)
	try:
		rs = frappe.db.sql(
			"""
			SELECT {gf} AS label, COUNT(*) AS value
			FROM `tabAir Shipment`
			WHERE {where}
			GROUP BY {gf}
			ORDER BY value DESC
			LIMIT %s
			""".format(gf=group_field, where=" AND ".join(conditions)),
			tuple(values + [n]),
			as_dict=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "ct_top_air_count {0}".format(group_field))
		rs = []
	return [{"label": r["label"], "value": flt(r["value"])} for r in rs]


def _top_outsourced(filters, doctype, date_field, group_field, n, year_start, year_end):
	conditions = [
		"{0} BETWEEN %s AND %s".format(date_field),
		"ct_outsourced = 1",
		"{0} IS NOT NULL".format(group_field),
		"{0} != ''".format(group_field),
	]
	values = [year_start, year_end]
	dim_conditions, dim_values = _dim_clauses(filters)
	conditions.extend(dim_conditions)
	values.extend(dim_values)
	try:
		rs = frappe.db.sql(
			"""
			SELECT {gf} AS label, COUNT(*) AS value
			FROM `tab{dt}`
			WHERE {where}
			GROUP BY {gf}
			ORDER BY value DESC
			LIMIT %s
			""".format(gf=group_field, dt=doctype, where=" AND ".join(conditions)),
			tuple(values + [n]),
			as_dict=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "ct_top_outsourced {0}".format(doctype))
		rs = []
	return [{"label": r["label"], "value": flt(r["value"])} for r in rs]


def _top_suppliers(filters, n, year_start, year_end):
	"""Top suppliers ranked by Purchase Invoice net total linked to org jobs."""
	conditions = ["pi.docstatus = 1", "pi.posting_date BETWEEN %s AND %s"]
	values = [year_start, year_end]
	dim_conditions, dim_values = _dim_clauses(filters, prefix="jn.")
	join_clause = ""
	if dim_conditions:
		join_clause = (
			"JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name "
			"JOIN `tabJob Number` jn ON jn.name = pii.job_number "
		)
		conditions.extend(dim_conditions)
		values.extend(dim_values)
	try:
		rs = frappe.db.sql(
			"""
			SELECT pi.supplier AS label, SUM(pi.base_net_total) AS value
			FROM `tabPurchase Invoice` pi
			{join}
			WHERE {where}
			GROUP BY pi.supplier
			ORDER BY value DESC
			LIMIT %s
			""".format(join=join_clause, where=" AND ".join(conditions)),
			tuple(values + [n]),
			as_dict=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "ct_top_suppliers")
		rs = []
	return [{"label": r["label"], "value": flt(r["value"])} for r in rs]


# ----------------------------------------------------------------------------- #
# Cost Center cross-module operations summary                                   #
# ----------------------------------------------------------------------------- #


@frappe.whitelist()
def get_trips_per_month(organization, fiscal_year=None):
	"""Monthly Transport Job trips for the org."""
	filters = resolve_org_filters(organization)
	year = int(fiscal_year) if fiscal_year else int(nowdate()[:4])
	conditions = ["booking_date BETWEEN %s AND %s"]
	values = ["{0}-01-01".format(year), "{0}-12-31".format(year)]
	dim_conditions, dim_values = _dim_clauses(filters)
	conditions.extend(dim_conditions)
	values.extend(dim_values)
	try:
		rs = frappe.db.sql(
			"""
			SELECT DATE_FORMAT(booking_date, '%%Y-%%m') AS period, COUNT(*) AS trips
			FROM `tabTransport Job`
			WHERE {where}
			GROUP BY DATE_FORMAT(booking_date, '%%Y-%%m')
			ORDER BY period
			""".format(where=" AND ".join(conditions) or "1=1"),
			tuple(values),
			as_dict=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "ct_trips_per_month")
		rs = []
	return [{"period": r["period"], "trips": int(r["trips"])} for r in rs]


@frappe.whitelist()
def get_handling_in_out(organization, fiscal_year=None):
	"""Monthly inbound and outbound counts from Warehouse Job. Categorizes
	by ``type`` field on Warehouse Job.
	"""
	filters = resolve_org_filters(organization)
	year = int(fiscal_year) if fiscal_year else int(nowdate()[:4])
	conditions = ["job_open_date BETWEEN %s AND %s"]
	values = ["{0}-01-01".format(year), "{0}-12-31".format(year)]
	dim_conditions, dim_values = _dim_clauses(filters)
	conditions.extend(dim_conditions)
	values.extend(dim_values)
	try:
		rs = frappe.db.sql(
			"""
			SELECT DATE_FORMAT(job_open_date, '%%Y-%%m') AS period,
			       SUM(CASE WHEN type = 'Putaway' THEN 1 ELSE 0 END) AS inbound,
			       SUM(CASE WHEN type = 'Pick' THEN 1 ELSE 0 END) AS outbound
			FROM `tabWarehouse Job`
			WHERE {where}
			GROUP BY DATE_FORMAT(job_open_date, '%%Y-%%m')
			ORDER BY period
			""".format(where=" AND ".join(conditions) or "1=1"),
			tuple(values),
			as_dict=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "ct_handling_in_out")
		rs = []
	return [{"period": r["period"], "inbound": int(r.get("inbound") or 0), "outbound": int(r.get("outbound") or 0)} for r in rs]


# ----------------------------------------------------------------------------- #
# Pipeline & Risk                                                               #
# ----------------------------------------------------------------------------- #


@frappe.whitelist()
def get_pipeline_summary(organization, category=None):
	"""Aggregate Pipeline Entry by stage."""
	conditions = ["organization = %s"]
	values = [organization]
	if category:
		conditions.append("category = %s")
		values.append(category)
	rs = frappe.db.sql(
		"""
		SELECT stage, COUNT(*) AS count,
		       SUM(estimated_gp) AS estimated_gp,
		       SUM(weighted_gp) AS weighted_gp
		FROM `tabPipeline Entry`
		WHERE {where}
		GROUP BY stage
		""".format(where=" AND ".join(conditions)),
		tuple(values),
		as_dict=True,
	)
	return [
		{
			"stage": r["stage"],
			"count": int(r["count"]),
			"estimated_gp": flt(r["estimated_gp"]),
			"weighted_gp": flt(r["weighted_gp"]),
		}
		for r in rs
	]


@frappe.whitelist()
def get_risk_register_summary(organization):
	"""Aggregate open Risk Register Entries by score band."""
	bands = {"Low (1-5)": 0, "Medium (6-12)": 0, "High (13-20)": 0, "Critical (21-25)": 0}
	rs = frappe.db.sql(
		"""
		SELECT score FROM `tabRisk Register Entry`
		WHERE organization = %s AND status IN ('Open', 'Mitigated')
		""",
		(organization,),
		as_dict=True,
	)
	for r in rs:
		s = int(r["score"] or 0)
		if s <= 5:
			bands["Low (1-5)"] += 1
		elif s <= 12:
			bands["Medium (6-12)"] += 1
		elif s <= 20:
			bands["High (13-20)"] += 1
		else:
			bands["Critical (21-25)"] += 1
	return [{"band": k, "count": v} for k, v in bands.items()]


# ----------------------------------------------------------------------------- #
# Number Card helper                                                            #
# ----------------------------------------------------------------------------- #


@frappe.whitelist()
def kpi_card_value(filters=None):
	"""Compute a single scalar value for a Control Tower Number Card.

	Used by ``Custom`` Number Cards seeded by ``install._ensure_number_card``
	(non-``Document Type`` metrics). Filters carry the org + metric key:

	    ``{"organization": "...", "metric": "open_job_files_count"}``

	Returns ``{"value": <number>, "fieldtype": "Float|Int|Currency"}``.
	"""
	if isinstance(filters, str):
		filters = frappe.parse_json(filters) or {}
	if not isinstance(filters, dict):
		filters = {}
	organization = filters.get("organization")
	metric = filters.get("metric")
	if not organization or not metric:
		return {"value": 0}

	value = 0
	fieldtype = "Float"
	try:
		if metric == "gp_ytd":
			value = (get_gp_summary(organization) or {}).get("gp_ytd", 0)
			fieldtype = "Currency"
		elif metric == "gp_prior_ytd":
			value = (get_gp_summary(organization) or {}).get("gp_prior_ytd", 0)
			fieldtype = "Currency"
		elif metric == "gp_target":
			value = (get_gp_summary(organization) or {}).get("gp_target", 0)
			fieldtype = "Currency"
		elif metric == "gp_vs_target_pct":
			value = (get_gp_summary(organization) or {}).get("gp_vs_target_pct", 0)
			fieldtype = "Percent"
		elif metric == "open_job_files_count":
			value = (get_jobs_kpi(organization) or {}).get("open_job_files_count", 0)
			fieldtype = "Int"
		elif metric == "avg_age_open_jobs":
			value = (get_jobs_kpi(organization) or {}).get("avg_age_open_jobs", 0)
			fieldtype = "Float"
		elif metric == "jobs_handled_count":
			value = (get_jobs_kpi(organization) or {}).get("jobs_handled_count", 0)
			fieldtype = "Int"
		elif metric == "avg_lead_time_per_milestone":
			value = get_avg_lead_time(organization) or 0
			fieldtype = "Float"
		elif metric == "returned_billings_count":
			value = frappe.db.count(
				"Returned Billing",
				{"organization": organization, "resolution_status": ["in", ["Open", "Investigating"]]},
			)
			fieldtype = "Int"
		elif metric == "outsourced_jobs_count":
			value = frappe.db.sql(
				"""SELECT
					(SELECT COUNT(*) FROM `tabTransport Job` WHERE IFNULL(ct_outsourced,0)=1)
					+ (SELECT COUNT(*) FROM `tabDeclaration` WHERE IFNULL(ct_outsourced,0)=1)
				"""
			)[0][0] or 0
			fieldtype = "Int"
		elif metric == "turnover_rate_trend":
			# Approx: turnovers in current year / headcount estimate.
			year = nowdate()[:4]
			leavers = frappe.db.count(
				"HR Turnover Event",
				{"separation_date": [">=", "{0}-01-01".format(year)]},
			)
			value = leavers
			fieldtype = "Int"
		elif metric == "avg_ticket_tat":
			row = frappe.db.sql(
				"SELECT AVG(tat_hours) FROM `tabIT Ticket` WHERE tat_hours IS NOT NULL"
			)
			value = (row and row[0][0]) or 0
			fieldtype = "Float"
		elif metric == "unbilled_shipment_count":
			# Heuristic: jobs with no Sales Invoice linked.
			row = frappe.db.sql(
				"""SELECT COUNT(*) FROM `tabSea Shipment` WHERE job_status NOT IN ('Cancelled','Completed') AND IFNULL(sales_invoice,'')=''"""
			)
			value = (row and row[0][0]) or 0
			fieldtype = "Int"
	except Exception:
		frappe.log_error(frappe.get_traceback(), "kpi_card_value({0}, {1})".format(organization, metric))
		value = 0

	return {"value": flt(value), "fieldtype": fieldtype}


# ----------------------------------------------------------------------------- #
# Workspace helper                                                              #
# ----------------------------------------------------------------------------- #


@frappe.whitelist()
def get_organizations_by_group():
	"""Return enabled organizations grouped by ``group`` for workspace tiles."""
	rows = frappe.get_all(
		"Control Tower Organization",
		filters={"enabled": 1},
		fields=["name", "organization_name", "group", "home_module", "description"],
		order_by="group asc, organization_name asc",
	)
	grouped = defaultdict(list)
	for r in rows:
		grouped[r["group"]].append(r)
	return {
		"Profit Center": grouped.get("Profit Center", []),
		"Cost Center": grouped.get("Cost Center", []),
		"Resource Center": grouped.get("Resource Center", []),
	}
