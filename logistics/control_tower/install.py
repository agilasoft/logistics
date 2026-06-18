# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
"""Control Tower install / migrate seeder.

Idempotently materializes the 22 Control Tower Organization records and all
their derived Dashboard Charts, Number Cards, and Dashboards from the
canonical ``seed_data.ORGANIZATIONS`` registry.

Run automatically via ``after_install`` and ``after_migrate`` hooks.

Re-running is safe: missing records are created; existing records are
left intact so admin edits in the UI are preserved. Use
``logistics.control_tower.install.rebuild(force=True)`` to drop and recreate
Control Tower charts/cards/dashboards (does NOT touch user data DocTypes
like Pipeline Entry / Risk Register Entry / GP Target / etc.).
"""

from __future__ import unicode_literals

import json

import frappe
from frappe.utils import slug

from logistics.control_tower.seed_data import ORGANIZATIONS, METRICS, metric_label


CT_MODULE = "Control Tower"


# ----------------------------------------------------------------------------- #
# Public entrypoints                                                            #
# ----------------------------------------------------------------------------- #


def after_install():
	"""Called once when the app is freshly installed."""
	_run_safe(_seed_roles)
	_run_safe(_seed_organizations)
	_run_safe(_seed_gp_targets)
	_run_safe(_seed_charts_cards_dashboards)


def after_migrate():
	"""Called after every ``bench migrate``. Idempotent."""
	if frappe.flags.in_install:
		return
	_run_safe(_seed_roles)
	_run_safe(_seed_organizations)
	_run_safe(_seed_gp_targets)
	_run_safe(_seed_charts_cards_dashboards)


def rebuild(force=False):
	"""Manually re-seed (called via ``bench execute``).

	If ``force=True`` is passed, drops all Control-Tower-owned Dashboard,
	Dashboard Chart, and Number Card records first, then re-creates them.
	"""
	if force:
		_purge_generated()
	after_migrate()


def _run_safe(fn):
	try:
		fn()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Control Tower seeder: {0}".format(fn.__name__))


# ----------------------------------------------------------------------------- #
# Roles                                                                         #
# ----------------------------------------------------------------------------- #


def _seed_roles():
	for role_name in ("Control Tower Manager", "Control Tower Viewer"):
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc({
				"doctype": "Role",
				"role_name": role_name,
				"desk_access": 1,
			}).insert(ignore_permissions=True)


# ----------------------------------------------------------------------------- #
# Organizations                                                                 #
# ----------------------------------------------------------------------------- #


def _seed_organizations():
	"""Create the 22 Control Tower Organization records.

	The default dimension hints in ``seed_data.ORGANIZATIONS`` reference
	ERPNext masters (Profit Center, Branch, Cost Center, Company) that may
	not exist on a fresh tenant. We do NOT auto-create those masters - the
	seeder simply skips any mapping value whose target row is missing and
	logs a warning so the operator can wire it up post-install.
	"""
	for spec in ORGANIZATIONS:
		name = spec["organization_name"]
		if frappe.db.exists("Control Tower Organization", name):
			continue
		doc = frappe.new_doc("Control Tower Organization")
		doc.organization_name = name
		doc.group = spec["group"]
		if spec.get("home_module") and frappe.db.exists("Module Def", spec["home_module"]):
			doc.home_module = spec["home_module"]
		doc.description = spec.get("description")
		doc.enabled = 1 if spec.get("enabled", 1) else 0
		for mapping in spec.get("default_mappings") or []:
			row = {
				"company": _existing("Company", mapping.get("company"), name),
				"branch": _existing("Branch", mapping.get("branch"), name),
				"cost_center": _existing("Cost Center", mapping.get("cost_center"), name),
				"profit_center": _existing("Profit Center", mapping.get("profit_center"), name),
			}
			# Only add the row when at least one dimension survived.
			if any(row.values()):
				doc.append("mappings", row)
		doc.insert(ignore_permissions=True, ignore_links=True)


def _existing(doctype, value, org_name):
	"""Return ``value`` if it exists in ``doctype``; otherwise None and log."""
	if not value:
		return None
	if frappe.db.exists(doctype, value):
		return value
	frappe.log_error(
		"Control Tower org '{0}': default {1} '{2}' does not exist. Mapping field left blank.".format(
			org_name, doctype, value
		),
		"Control Tower seeder",
	)
	return None


def _seed_gp_targets():
	"""Seed a placeholder Annual GP Target for the current FY for every Profit
	Center org so the dashboard shows 0 PHP target rather than blank."""
	from frappe.utils import nowdate
	year = nowdate()[:4]
	if not frappe.db.exists("Fiscal Year", year):
		return
	for spec in ORGANIZATIONS:
		if spec.get("group") != "Profit Center":
			continue
		if frappe.db.exists("Control Tower GP Target", {"organization": spec["organization_name"], "fiscal_year": year}):
			continue
		try:
			frappe.get_doc({
				"doctype": "Control Tower GP Target",
				"organization": spec["organization_name"],
				"fiscal_year": year,
				"target_amount": 0,
				"currency": "PHP",
				"notes": "Auto-seeded placeholder target. Update with actual figure.",
			}).insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "GP target seed {0}".format(spec["organization_name"]))


# ----------------------------------------------------------------------------- #
# Dashboard Charts / Number Cards / Dashboards                                  #
# ----------------------------------------------------------------------------- #


# Per-metric specification:
#   kind          : "chart" / "number_card" / "both"
#   chart_type    : when kind in {"chart","both"}, one of "report"/"document"
#   report_name   : when chart_type=="report", the Script Report name
#   chart_viz     : "Bar" / "Line" / "Pie" / "Donut"
#   filters       : dict of base filters added to filters_json
#   card_function : when kind in {"number_card","both"}, ("function", "value_field" or None)
#                   - ("Count", None) - count records
#                   - ("Sum", "fieldname")
#                   - ("Custom", None) - rely on filter
# Each spec receives the org's name + filters to specialise.
METRIC_SPECS = {
	# Profit Center headline KPIs
	"gp_ytd": {
		"kind": "number_card",
		"report_name": "CT GP Summary",
		"card_label": "Gross Profit (YTD)",
	},
	"gp_prior_ytd": {"kind": "number_card", "report_name": "CT GP Summary", "card_label": "GP (Prior YTD)"},
	"gp_target": {"kind": "number_card", "report_name": "CT GP Summary", "card_label": "GP Target"},
	"gp_vs_target_pct": {"kind": "number_card", "report_name": "CT GP Summary", "card_label": "GP vs Target %"},
	"gp_3year_compare": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "CT GP Summary",
		"chart_viz": "Bar",
	},
	"gp_metro_vs_luzon": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "Job Branch and Profit Center PL",
		"chart_viz": "Bar",
	},
	"gp_per_network": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "Job Customer Profitability",
		"chart_viz": "Bar",
	},
	"top10_clients_by_gp": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "CT Top Clients by GP",
		"chart_viz": "Bar",
		"extra_filters": {"limit_n": 10},
	},
	"top5_clients_by_gp": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "CT Top Clients by GP",
		"chart_viz": "Bar",
		"extra_filters": {"limit_n": 5},
	},
	"top5_agents_sea_fcl_teu": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "CT Top Agents Volumes",
		"chart_viz": "Bar",
		"extra_filters": {"metric": "Sea FCL (TEU)", "limit_n": 5},
	},
	"top5_agents_sea_lcl_cbm": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "CT Top Agents Volumes",
		"chart_viz": "Bar",
		"extra_filters": {"metric": "Sea LCL (CBM)", "limit_n": 5},
	},
	"top5_agents_air_chw": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "CT Top Agents Volumes",
		"chart_viz": "Bar",
		"extra_filters": {"metric": "Air (CHW)", "limit_n": 5},
	},
	"top5_carriers_sea_fcl_teu": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "CT Top Carriers Volumes",
		"chart_viz": "Bar",
		"extra_filters": {"metric": "Sea FCL (TEU)", "limit_n": 5},
	},
	"top5_carriers_sea_lcl_cbm": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "CT Top Carriers Volumes",
		"chart_viz": "Bar",
		"extra_filters": {"metric": "Sea LCL (CBM)", "limit_n": 5},
	},
	"top5_carriers_air_chw": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "CT Top Carriers Volumes",
		"chart_viz": "Bar",
		"extra_filters": {"metric": "Air (CHW)", "limit_n": 5},
	},
	"top5_airlines": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "CT Top Carriers Volumes",
		"chart_viz": "Bar",
		"extra_filters": {"metric": "Airline (Count)", "limit_n": 5},
	},
	"top5_outsourced_truckers": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "CT Top Outsourced Truckers",
		"chart_viz": "Bar",
	},
	"top5_outsourced_brokers": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "CT Top Outsourced Brokers",
		"chart_viz": "Bar",
	},
	"top5_suppliers": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "CT Top Outsourced Truckers",  # repurposed: shows top N
		"chart_viz": "Bar",
	},
	"pipeline_list": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "CT Pipeline Listing",
		"chart_viz": "Bar",
	},
	"exhibits_pipeline_list": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "CT Pipeline Listing",
		"chart_viz": "Bar",
		"extra_filters": {"category": "Exhibits"},
	},
	"projects_pipeline_list": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "CT Pipeline Listing",
		"chart_viz": "Bar",
		"extra_filters": {"category": "Special Projects"},
	},
	"luxury_pipeline_list": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "CT Pipeline Listing",
		"chart_viz": "Bar",
		"extra_filters": {"category": "Luxury"},
	},
	"risk_register_list": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "CT Risk Register Listing",
		"chart_viz": "Bar",
	},
	# Cost Center KPIs (number cards mostly, plus by-module chart)
	"open_job_files_count": {"kind": "number_card", "report_name": "CT Jobs KPI", "card_label": "Open Job Files (#)"},
	"avg_age_open_jobs": {"kind": "number_card", "report_name": "CT Jobs KPI", "card_label": "Avg Age (days)"},
	"jobs_handled_count": {"kind": "number_card", "report_name": "CT Jobs KPI", "card_label": "Jobs Handled"},
	"avg_lead_time_per_milestone": {"kind": "number_card", "report_name": "CT Jobs KPI", "card_label": "Avg Lead Time (days)"},
	"returned_billings_count": {"kind": "number_card", "report_name": "CT Jobs KPI", "card_label": "Returned Billings (#)"},
	"outsourced_jobs_count": {"kind": "number_card", "report_name": "CT Top Outsourced Brokers", "card_label": "Outsourced Jobs (#)"},
	"trips_per_month": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "CT Trips Per Month",
		"chart_viz": "Bar",
	},
	"monthly_haulage_charge_to_file": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "CT Haulage Intercompany Charges",
		"chart_viz": "Bar",
	},
	"monthly_haulage_charge_to_asl": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "CT Haulage Intercompany Charges",
		"chart_viz": "Bar",
	},
	"vehicle_maintenance_due": {
		"kind": "chart",
		"chart_type": "document",
		"document_type": "Vehicle Maintenance Log",
		"chart_viz": "Bar",
		"chart_subtype": "Count",
		"based_on": "next_service_due",
		"timespan": "Last Year",
		"time_interval": "Monthly",
	},
	"facility_occupancy_pct": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "CT Facility Occupancy",
		"chart_viz": "Donut",
	},
	"handling_in_out_trend": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "CT Handling In Out",
		"chart_viz": "Bar",
	},
	# Resource Center
	"labor_cost_vs_budget": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "CT HR Summary",
		"chart_viz": "Bar",
		"global": True,
	},
	"turnover_rate_trend": {
		"kind": "number_card",
		"report_name": "CT HR Summary",
		"card_label": "Turnover Rate %",
		"global": True,
	},
	"open_vacancies_count": {
		"kind": "number_card",
		"document_type": "HR Vacancy",
		"card_label": "Open Vacancies",
		"card_function": "Count",
		"card_filters": [["HR Vacancy", "status", "in", ["Open", "Interviewing", "Offered"]]],
		"global": True,
	},
	"tardiness_ot_trend": {
		"kind": "chart",
		"chart_type": "document",
		"document_type": "HR Tardiness OT Entry",
		"chart_viz": "Bar",
		"chart_subtype": "Sum",
		"based_on": "period",
		"value_based_on": "ot_hours",
		"timespan": "Last Year",
		"time_interval": "Monthly",
		"global": True,
	},
	"tickets_ytd_count": {
		"kind": "number_card",
		"document_type": "IT Ticket",
		"card_label": "Tickets YTD",
		"card_function": "Count",
		"global": True,
	},
	"avg_ticket_tat": {
		"kind": "number_card",
		"report_name": "CT IT Summary",
		"card_label": "Avg Ticket TAT (h)",
		"global": True,
	},
	"uptime_trend": {
		"kind": "chart",
		"chart_type": "document",
		"document_type": "IT Uptime Log",
		"chart_viz": "Line",
		"chart_subtype": "Average",
		"based_on": "period",
		"value_based_on": "uptime_pct",
		"timespan": "Last Year",
		"time_interval": "Monthly",
		"global": True,
	},
	"security_incidents_count": {
		"kind": "number_card",
		"document_type": "IT Security Incident",
		"card_label": "Security Incidents YTD",
		"card_function": "Count",
		"global": True,
	},
	"collections_60plus_aging": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "Job Receivables Aging",
		"chart_viz": "Bar",
		"global": True,
	},
	"bad_accounts_total": {
		"kind": "number_card",
		"document_type": "Bad Account Entry",
		"card_label": "Bad Accounts (PHP)",
		"card_function": "Sum",
		"card_value_field": "amount",
		"global": True,
	},
	"unbilled_shipment_count": {
		"kind": "number_card",
		"report_name": "CT Accounting Finance Summary",
		"card_label": "Unbilled Shipments (#)",
		"global": True,
	},
	"cash_advances_summary": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "Cash Advance Liquidation Aging",
		"chart_viz": "Bar",
		"global": True,
	},
	"container_deposit_summary": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "Container Deposit Report",
		"chart_viz": "Bar",
		"global": True,
	},
	"credit_lines_exposure": {
		"kind": "number_card",
		"document_type": "Client Credit Line",
		"card_label": "Credit Exposure (PHP)",
		"card_function": "Sum",
		"card_value_field": "exposure_amount",
		"global": True,
	},
	"investment_holdings_summary": {
		"kind": "number_card",
		"document_type": "Investment Holding",
		"card_label": "Investments (PHP)",
		"card_function": "Sum",
		"card_value_field": "principal",
		"global": True,
	},
	"payables_aging": {
		"kind": "chart",
		"chart_type": "report",
		"report_name": "Job Payables Aging",
		"chart_viz": "Bar",
		"global": True,
	},
	"bank_recon_discrepancies_total": {
		"kind": "number_card",
		"document_type": "Bank Reconciliation Discrepancy",
		"card_label": "Bank Recon Discrepancies",
		"card_function": "Count",
		"card_filters": [["Bank Reconciliation Discrepancy", "status", "in", ["Open", "Investigating"]]],
		"global": True,
	},
	"supplier_cash_bond_total": {
		"kind": "number_card",
		"document_type": "Supplier Cash Bond",
		"card_label": "Supplier Cash Bond (PHP)",
		"card_function": "Sum",
		"card_value_field": "amount",
		"card_filters": [["Supplier Cash Bond", "refund_status", "in", ["Outstanding", "Partially Refunded"]]],
		"global": True,
	},
}


def _seed_charts_cards_dashboards():
	"""Create per-org Dashboard Charts, Number Cards, and Dashboards.

	Notes on idempotency / naming:
	  * ``Dashboard Chart`` autonames from ``chart_name``.
	  * ``Number Card`` autonames from ``label`` (if ``name`` is unset).
	    To make seeded cards uniquely addressable, the seeder embeds the org
	    name in the label for per-org cards and uses the ``card_label`` alone
	    for ``global`` cards (shared across all orgs that subscribe to them).
	  * Everything is marked ``is_standard=0`` so the
	    ``developer_mode`` ``on_update`` hook does not try to materialise the
	    record as JSON files on disk (the install does not need write access
	    to the app directory; fixtures handle export when a developer runs
	    ``bench export-fixtures``).
	"""
	for spec in ORGANIZATIONS:
		org = spec["organization_name"]
		dashboard_card_refs = []
		dashboard_chart_refs = []
		for metric_key in spec.get("metrics") or []:
			ms = METRIC_SPECS.get(metric_key)
			if not ms:
				continue
			kind = ms.get("kind", "chart")
			if kind in ("chart", "both"):
				chart_name = _ensure_dashboard_chart(org, metric_key, ms)
				if chart_name:
					dashboard_chart_refs.append(chart_name)
			if kind in ("number_card", "both"):
				card_name = _ensure_number_card(org, metric_key, ms)
				if card_name:
					dashboard_card_refs.append(card_name)
		# If the org has no chart-kind metric, mint a per-org headline chart
		# so its Dashboard renders something meaningful (rather than the
		# previous behaviour of borrowing the first CT chart found).
		if not dashboard_chart_refs:
			fallback_chart = _ensure_headline_chart(org, spec)
			if fallback_chart:
				dashboard_chart_refs.append(fallback_chart)
		_ensure_dashboard(org, dashboard_chart_refs, dashboard_card_refs)


def _slug(text):
	return slug(text or "").replace("-", "_")


def _chart_record_name(org, metric_key):
	return "CT - {0} - {1}".format(org, metric_label(metric_key))


def _card_label(org, metric_key, ms):
	"""Return the canonical Number Card label (and therefore its name)."""
	base = ms.get("card_label") or metric_label(metric_key)
	if ms.get("global"):
		return base
	return "{0} - {1}".format(base, org)


def _ensure_dashboard_chart(org, metric_key, ms):
	name = _chart_record_name(org, metric_key)
	if frappe.db.exists("Dashboard Chart", name):
		# Defensively flip ``is_standard=0`` to suppress file-export
		# side-effects on subsequent saves by other consumers.
		frappe.db.set_value("Dashboard Chart", name, "is_standard", 0, update_modified=False)
		return name
	chart_type_key = ms.get("chart_type", "report")
	# Skip when the referenced source (Report or DocType) is missing on this
	# tenant. This keeps the seeder usable on partial deployments without
	# emitting noisy errors per missing link.
	if chart_type_key == "report":
		if not ms.get("report_name") or not frappe.db.exists("Report", ms["report_name"]):
			return None
	elif chart_type_key == "document":
		if not ms.get("document_type") or not frappe.db.exists("DocType", ms["document_type"]):
			return None
	doc_data = {
		"doctype": "Dashboard Chart",
		"chart_name": name,
		"module": CT_MODULE,
		"is_public": 1,
		"is_standard": 0,
		"type": ms.get("chart_viz", "Bar"),
		"timeseries": 0,
		"time_interval": ms.get("time_interval", "Monthly"),
		"timespan": ms.get("timespan", "Last Year"),
		"number_of_groups": 0,
		"use_report_chart": 0,
	}
	if chart_type_key == "report":
		doc_data["chart_type"] = "Report"
		doc_data["report_name"] = ms.get("report_name")
		filters = {"organization": org}
		filters.update(ms.get("extra_filters") or {})
		doc_data["filters_json"] = json.dumps(filters)
		doc_data["use_report_chart"] = 1
	elif chart_type_key == "document":
		doc_data["chart_type"] = ms.get("chart_subtype", "Count")
		doc_data["document_type"] = ms.get("document_type")
		if ms.get("based_on"):
			doc_data["based_on"] = ms["based_on"]
			doc_data["timeseries"] = 1
		if ms.get("value_based_on"):
			doc_data["value_based_on"] = ms["value_based_on"]
		doc_data["filters_json"] = json.dumps([])
	try:
		frappe.get_doc(doc_data).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "ensure_dashboard_chart {0}".format(name))
		return None
	return name


def _ensure_headline_chart(org, spec):
	"""Create a fallback per-org headline chart for orgs whose metric set is
	100% number-card driven. Uses the same Script Report that powers the
	org's first number card so the chart and cards stay consistent."""
	report_name = None
	group = spec.get("group")
	if group == "Cost Center":
		report_name = "CT Jobs KPI"
	elif group == "Resource Center":
		# Choose by home module
		mod = (spec.get("home_module") or "").lower()
		if "account" in mod:
			report_name = "CT Accounting Finance Summary"
		elif "control tower" in mod and "tech" in (spec.get("organization_name") or "").lower():
			report_name = "CT IT Summary"
		else:
			report_name = "CT HR Summary"
	else:
		report_name = "CT GP Summary"
	if not report_name or not frappe.db.exists("Report", report_name):
		return None
	chart_name = "CT - {0} - Headline".format(org)
	if frappe.db.exists("Dashboard Chart", chart_name):
		return chart_name
	try:
		frappe.get_doc({
			"doctype": "Dashboard Chart",
			"chart_name": chart_name,
			"module": CT_MODULE,
			"is_public": 1,
			"is_standard": 0,
			"type": "Bar",
			"chart_type": "Report",
			"report_name": report_name,
			"timeseries": 0,
			"time_interval": "Monthly",
			"timespan": "Last Year",
			"number_of_groups": 0,
			"use_report_chart": 1,
			"filters_json": json.dumps({"organization": org}),
		}).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "ensure_headline_chart {0}".format(chart_name))
		return None
	return chart_name


def _ensure_number_card(org, metric_key, ms):
	"""Create / reuse a Number Card.

	* ``Document Type`` cards are inserted once and reused across orgs by
	  ``global=True`` metrics. (The shared card uses the bare label as its
	  canonical name; a per-org wrapper would inflate the count without
	  giving the user a different number.)
	* Report-driven (per-org) cards become ``Custom`` cards calling
	  ``logistics.control_tower.api.kpi_card_value`` which runs the same
	  aggregation API used by the Script Reports.
	"""
	label = _card_label(org, metric_key, ms)
	if frappe.db.exists("Number Card", label):
		frappe.db.set_value("Number Card", label, "is_standard", 0, update_modified=False)
		return label
	# Skip when underlying source is missing.
	if ms.get("document_type") and not frappe.db.exists("DocType", ms["document_type"]):
		return None
	if not ms.get("document_type") and ms.get("report_name") and not frappe.db.exists("Report", ms["report_name"]):
		return None
	if ms.get("document_type"):
		filters = ms.get("card_filters") or []
		doc_data = {
			"doctype": "Number Card",
			"label": label,
			"module": CT_MODULE,
			"is_public": 1,
			"is_standard": 0,
			"type": "Document Type",
			"document_type": ms["document_type"],
			"function": ms.get("card_function", "Count"),
			"aggregate_function_based_on": ms.get("card_value_field", ""),
			"filters_json": json.dumps(filters),
			"dynamic_filters_json": "[]",
		}
	else:
		doc_data = {
			"doctype": "Number Card",
			"label": label,
			"module": CT_MODULE,
			"is_public": 1,
			"is_standard": 0,
			"type": "Custom",
			"method": "logistics.control_tower.api.kpi_card_value",
			"document_type": "Control Tower Organization",
			"filters_json": json.dumps({
				"organization": org,
				"metric": metric_key,
				"report_name": ms.get("report_name") or "",
			}),
			"dynamic_filters_json": "[]",
		}
	try:
		frappe.get_doc(doc_data).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "ensure_number_card {0}".format(label))
		return None
	return label


def _dashboard_record_name(org):
	return "Control Tower - {0}".format(org)


def _ensure_dashboard(org, chart_names, card_names):
	name = _dashboard_record_name(org)
	exists = frappe.db.exists("Dashboard", name)
	if exists:
		doc = frappe.get_doc("Dashboard", name)
		doc.set("charts", [])
		doc.set("cards", [])
		# Suppress the file-export side-effect of ``is_standard=1``; the
		# seeder fully owns these dashboards, fixtures handle export.
		doc.is_standard = 0
	else:
		doc = frappe.new_doc("Dashboard")
		doc.dashboard_name = name
		doc.module = CT_MODULE
		doc.is_standard = 0
		doc.is_default = 0
	for cn in chart_names:
		doc.append("charts", {"chart": cn, "width": "Half"})
	for cn in card_names:
		doc.append("cards", {"card": cn})
	if not doc.get("charts"):
		# Should not happen now that _ensure_headline_chart runs first, but
		# guard against a missing report (e.g. fresh install with no CT
		# reports synced yet).
		return None
	try:
		if exists:
			doc.save(ignore_permissions=True)
		else:
			doc.insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "ensure_dashboard {0}".format(name))
		return None
	return name


# ----------------------------------------------------------------------------- #
# Force rebuild helper                                                          #
# ----------------------------------------------------------------------------- #


def _purge_generated():
	"""Drop all CT-owned Dashboards / Dashboard Charts / Number Cards.

	Source-of-truth user data (organizations, mappings, pipeline entries,
	risk register, returned billings, GP targets, HR/IT/A&F trackers) is
	NEVER deleted.
	"""
	# Drop Dashboards first to release child-table FK refs.
	for doctype in ("Dashboard", "Dashboard Chart", "Number Card"):
		rows = frappe.get_all(doctype, filters={"module": CT_MODULE}, pluck="name")
		for row in rows:
			try:
				frappe.delete_doc(doctype, row, force=True, ignore_permissions=True)
			except Exception:
				frappe.log_error(frappe.get_traceback(), "purge {0} {1}".format(doctype, row))
