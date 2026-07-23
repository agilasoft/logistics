# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Air Freight Control Tower dashboard API.

Aggregates ATN Airfreight Control Tower KPIs into a single payload for the
``air-freight-control-tower`` desk page:

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
from frappe.utils import flt, nowdate

DEFAULT_ORGANIZATION = "ATN Airfreight"
AIR_MODULES = ["Air Shipment"]


@frappe.whitelist()
def get_dashboard_data(organization=None, fiscal_year=None):
	"""Return all Air Freight Control Tower metrics in one call.

	Falls back to ``ATN Airfreight`` when organization is blank. Job KPIs are
	scoped to Air Shipment so the page stays air-freight specific even when
	org dimension mappings are empty (wildcard).
	"""
	organization = (organization or "").strip() or DEFAULT_ORGANIZATION
	year = int(fiscal_year) if fiscal_year else int(nowdate()[:4])

	from logistics.control_tower.api import get_jobs_kpi, get_top_n

	kpi = get_jobs_kpi(organization, modules=AIR_MODULES, fiscal_year=year) or {}
	airlines = get_top_n(organization, "airline", n=5, fiscal_year=year) or []

	# Normalize airline rows for the chart / ranking list.
	top_airlines = []
	for row in airlines:
		top_airlines.append({
			"label": row.get("label") or _("Unknown"),
			"value": flt(row.get("value") or 0),
		})

	max_airline = max([r["value"] for r in top_airlines], default=0) or 1

	return {
		"organization": organization,
		"fiscal_year": year,
		"as_of": nowdate(),
		"kpis": {
			"open_job_files_count": int(kpi.get("open_job_files_count") or 0),
			"avg_age_open_jobs": round(flt(kpi.get("avg_age_open_jobs") or 0), 1),
			"jobs_handled_count": int(kpi.get("jobs_handled_count") or 0),
			"avg_lead_time_per_milestone": round(flt(kpi.get("avg_lead_time_per_milestone") or 0), 1),
			"returned_billings_count": int(kpi.get("returned_billings_count") or 0),
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
def get_organizations():
	"""Organizations available for the Air Freight Control Tower filter."""
	preferred = DEFAULT_ORGANIZATION
	rows = frappe.get_all(
		"Control Tower Organization",
		filters={"enabled": 1},
		fields=["name", "organization_name", "group", "home_module"],
		order_by="organization_name asc",
	)
	# Prefer Air Freight home module orgs, then the rest.
	air_first = [r for r in rows if (r.get("home_module") or "") == "Air Freight"]
	other = [r for r in rows if (r.get("home_module") or "") != "Air Freight"]
	ordered = air_first + other
	if not ordered:
		ordered = [{
			"name": preferred,
			"organization_name": preferred,
			"group": "Cost Center",
			"home_module": "Air Freight",
		}]
	return {"default": preferred, "organizations": ordered}
