# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
"""Canonical Control Tower Organization registry.

Source of truth for the 22 organizations from the Operations Meeting data sheet.
Consumed by ``install.py`` to seed ``Control Tower Organization`` records and by
``api.py`` / reports for any reverse-lookups that need the static metadata
(home module, group, layout hints).

Each org row is a ``dict`` with:

  organization_name : unique display name (also the primary key)
  group             : one of ``Profit Center`` / ``Cost Center`` / ``Resource Center``
  home_module       : Module Def name (must exist in ``logistics/modules.txt``
                      or in ERPNext core, e.g. ``Accounts``)
  description       : short blurb shown on the registry list view
  enabled           : 1 if the org should appear in the workspace by default
  default_mappings  : list of partial dimension hints; missing keys mean wildcard.
                      The install seeder only writes mapping rows for orgs that
                      do not already have any. Manual edits in the UI are
                      preserved across migrations.
  metrics           : ordered list of metric keys (drawn from ``METRICS`` below)
                      used by the dashboard generator to assemble the per-org
                      Dashboard layout. The keys are stable identifiers - they
                      double as chart / number-card name suffixes.
"""

from __future__ import unicode_literals

# Stable metric identifiers used both as Number Card / Dashboard Chart name
# suffixes and as routing keys into the aggregation API.
METRICS = {
    # Profit-center headline KPIs
    "gp_ytd": "Gross Profit (YTD)",
    "gp_prior_ytd": "Gross Profit (Prior YTD)",
    "gp_target": "Gross Profit Target",
    "gp_vs_target_pct": "GP vs Target %",
    "gp_3year_compare": "Gross Profit 3-Year Compare",
    "gp_metro_vs_luzon": "GP Metro Manila vs Luzon",
    "gp_per_network": "GP per Agent Network",
    # Top-N rankings
    "top10_clients_by_gp": "Top 10 Clients (GP)",
    "top5_clients_by_gp": "Top 5 Clients (GP)",
    "top5_agents_sea_fcl_teu": "Top 5 Agents - Sea FCL (TEU)",
    "top5_agents_sea_lcl_cbm": "Top 5 Agents - Sea LCL (CBM)",
    "top5_agents_air_chw": "Top 5 Agents - Air (CHW)",
    "top5_carriers_sea_fcl_teu": "Top 5 Carriers - Sea FCL (TEU)",
    "top5_carriers_sea_lcl_cbm": "Top 5 Carriers - Sea LCL (CBM)",
    "top5_carriers_air_chw": "Top 5 Carriers - Air (CHW)",
    "top5_airlines": "Top 5 Airlines",
    "top5_outsourced_truckers": "Top 5 Outsourced Truckers",
    "top5_outsourced_brokers": "Top 5 Outsourced Brokers",
    "top5_suppliers": "Top 5 Suppliers",
    # Pipeline / risk register
    "pipeline_list": "Pipeline",
    "exhibits_pipeline_list": "Exhibits Pipeline",
    "projects_pipeline_list": "Projects Pipeline",
    "luxury_pipeline_list": "Luxury Pipeline",
    "risk_register_list": "Risk Register",
    # Operations KPIs
    "open_job_files_count": "Open Job Files (#)",
    "avg_age_open_jobs": "Avg Age of Open Jobs (days)",
    "jobs_handled_count": "Job Files Handled (#)",
    "avg_lead_time_per_milestone": "Avg Lead Time per Milestone (days)",
    "returned_billings_count": "Returned Billings (#)",
    "outsourced_jobs_count": "Outsourced Job Files (#)",
    "trips_per_month": "Trips per Month",
    "monthly_haulage_charge_to_file": "Monthly Haulage Charge to File",
    "monthly_haulage_charge_to_asl": "Monthly Haulage Charge to ASL",
    "vehicle_maintenance_due": "Vehicle Maintenance Due",
    "facility_occupancy_pct": "Facility Occupancy %",
    "handling_in_out_trend": "Handling In and Out",
    # HR
    "labor_cost_vs_budget": "Labor Cost YTD vs Budget",
    "turnover_rate_trend": "Turnover Rate",
    "open_vacancies_count": "Open Vacancies (#)",
    "tardiness_ot_trend": "Tardiness & OT",
    # IT
    "tickets_ytd_count": "IT Tickets Served YTD",
    "avg_ticket_tat": "Average Ticket TAT",
    "uptime_trend": "System / Network Uptime",
    "security_incidents_count": "Security Incidents",
    # Accounting & Finance
    "collections_60plus_aging": "Collections 60+ Aging",
    "bad_accounts_total": "Bad Accounts",
    "unbilled_shipment_count": "Unbilled Shipment Monitoring",
    "cash_advances_summary": "Cash Advances",
    "container_deposit_summary": "Container Deposit",
    "credit_lines_exposure": "Credit Lines & Exposure",
    "investment_holdings_summary": "Investment Holdings",
    "payables_aging": "Payables",
    "bank_recon_discrepancies_total": "Bank Recon Discrepancies",
    "supplier_cash_bond_total": "Supplier Cash Bond",
}

# Helper builders for default mapping hints - the seeder will only add these
# rows when no mapping row exists yet (manual edits preserved).
def _m(**kw):
    base = {"company": None, "branch": None, "cost_center": None, "profit_center": None}
    base.update(kw)
    return base


ORGANIZATIONS = [
    # ----------------------------- Profit Centers -----------------------------
    {
        "organization_name": "ATN Sales - Luzon",
        "group": "Profit Center",
        "home_module": "Pricing Center",
        "description": "ATN sales coverage for Luzon territory (Metro Manila + Luzon branches).",
        "enabled": 1,
        "default_mappings": [_m(profit_center="ATN Sales - Luzon")],
        "metrics": [
            "gp_ytd", "gp_prior_ytd", "gp_target", "gp_vs_target_pct",
            "gp_3year_compare", "top10_clients_by_gp",
            "top5_agents_sea_fcl_teu", "top5_agents_sea_lcl_cbm", "top5_agents_air_chw",
            "top5_carriers_sea_fcl_teu", "top5_carriers_sea_lcl_cbm", "top5_carriers_air_chw",
            "pipeline_list", "risk_register_list",
        ],
    },
    {
        "organization_name": "ATN Sales - VisMin",
        "group": "Profit Center",
        "home_module": "Pricing Center",
        "description": "ATN sales coverage for Visayas-Mindanao territory.",
        "enabled": 1,
        "default_mappings": [_m(profit_center="ATN Sales - VisMin")],
        "metrics": [
            "gp_ytd", "gp_prior_ytd", "gp_target", "gp_vs_target_pct",
            "gp_3year_compare", "top10_clients_by_gp",
            "top5_agents_sea_fcl_teu", "top5_agents_sea_lcl_cbm", "top5_agents_air_chw",
            "top5_carriers_sea_fcl_teu", "top5_carriers_sea_lcl_cbm", "top5_carriers_air_chw",
            "pipeline_list", "risk_register_list",
        ],
    },
    {
        "organization_name": "ATN Overseas Business Development",
        "group": "Profit Center",
        "home_module": "Pricing Center",
        "description": "ATN overseas business development desk (WIN / NAP networks).",
        "enabled": 1,
        "default_mappings": [_m(profit_center="ATN Overseas BD")],
        "metrics": [
            "gp_ytd", "gp_prior_ytd", "gp_target", "gp_3year_compare",
            "top10_clients_by_gp",
            "top5_carriers_sea_fcl_teu", "top5_carriers_sea_lcl_cbm", "top5_airlines",
            "gp_metro_vs_luzon", "gp_per_network",
        ],
    },
    {
        "organization_name": "ALTA Fairs & Exhibits",
        "group": "Profit Center",
        "home_module": "Exhibits",
        "description": "ALTA fairs and exhibits revenue line (Profit Center view).",
        "enabled": 1,
        "default_mappings": [_m(profit_center="ALTA Fairs & Exhibits")],
        "metrics": [
            "gp_ytd", "gp_prior_ytd", "gp_target", "gp_3year_compare",
            "exhibits_pipeline_list", "top10_clients_by_gp",
        ],
    },
    {
        "organization_name": "ATN Special Projects 1",
        "group": "Profit Center",
        "home_module": "Special Projects",
        "description": "ATN special projects portfolio - team 1.",
        "enabled": 1,
        "default_mappings": [_m(profit_center="ATN Special Projects 1")],
        "metrics": [
            "gp_ytd", "gp_prior_ytd", "gp_target", "gp_3year_compare",
            "projects_pipeline_list", "top5_clients_by_gp",
        ],
    },
    {
        "organization_name": "ATN Special Projects 2",
        "group": "Profit Center",
        "home_module": "Special Projects",
        "description": "ATN special projects portfolio - team 2.",
        "enabled": 1,
        "default_mappings": [_m(profit_center="ATN Special Projects 2")],
        "metrics": [
            "gp_ytd", "gp_prior_ytd", "gp_target", "gp_3year_compare",
            "projects_pipeline_list", "top5_clients_by_gp",
        ],
    },
    {
        "organization_name": "ASL Sales",
        "group": "Profit Center",
        "home_module": "Pricing Center",
        "description": "ASL sales line (Metro Manila + Luzon).",
        "enabled": 1,
        "default_mappings": [_m(profit_center="ASL Sales")],
        "metrics": [
            "gp_ytd", "gp_prior_ytd", "gp_target", "gp_3year_compare",
            "top10_clients_by_gp",
            "top5_agents_sea_fcl_teu", "top5_agents_sea_lcl_cbm", "top5_agents_air_chw",
            "top5_carriers_sea_fcl_teu", "top5_carriers_sea_lcl_cbm", "top5_carriers_air_chw",
            "gp_metro_vs_luzon", "pipeline_list",
        ],
    },
    {
        "organization_name": "ASL Overseas Business Development",
        "group": "Profit Center",
        "home_module": "Pricing Center",
        "description": "ASL overseas business development desk.",
        "enabled": 1,
        "default_mappings": [_m(profit_center="ASL Overseas BD")],
        "metrics": [
            "gp_ytd", "gp_prior_ytd", "gp_target", "gp_3year_compare",
            "top10_clients_by_gp",
            "top5_carriers_sea_fcl_teu", "top5_carriers_sea_lcl_cbm", "top5_airlines",
            "gp_metro_vs_luzon", "gp_per_network",
        ],
    },
    {
        "organization_name": "Luxury",
        "group": "Profit Center",
        "home_module": "High Value",
        "description": "Luxury / high value cargo line.",
        "enabled": 1,
        "default_mappings": [_m(profit_center="Luxury")],
        "metrics": [
            "gp_ytd", "gp_prior_ytd", "gp_target", "gp_3year_compare",
            "top10_clients_by_gp", "luxury_pipeline_list",
        ],
    },
    # ----------------------------- Cost Centers -----------------------------
    {
        "organization_name": "ATN Head Office Seafreight",
        "group": "Cost Center",
        "home_module": "Sea Freight",
        "description": "ATN head-office sea freight operations.",
        "enabled": 1,
        "default_mappings": [_m(cost_center="ATN Head Office Seafreight")],
        "metrics": [
            "open_job_files_count", "avg_age_open_jobs", "jobs_handled_count",
            "avg_lead_time_per_milestone", "returned_billings_count",
        ],
    },
    {
        "organization_name": "ATN Airfreight",
        "group": "Cost Center",
        "home_module": "Air Freight",
        "description": "ATN air freight operations.",
        "enabled": 1,
        "default_mappings": [_m(cost_center="ATN Airfreight")],
        "metrics": [
            "open_job_files_count", "avg_age_open_jobs", "jobs_handled_count",
            "avg_lead_time_per_milestone", "top5_airlines", "returned_billings_count",
        ],
    },
    {
        "organization_name": "ATN Brokerage",
        "group": "Cost Center",
        "home_module": "Customs",
        "description": "ATN customs brokerage operations.",
        "enabled": 1,
        "default_mappings": [_m(cost_center="ATN Brokerage")],
        "metrics": [
            "open_job_files_count", "avg_age_open_jobs", "jobs_handled_count",
            "avg_lead_time_per_milestone", "top5_outsourced_brokers",
            "returned_billings_count", "outsourced_jobs_count",
        ],
    },
    {
        "organization_name": "ATN Haulage",
        "group": "Cost Center",
        "home_module": "Transport",
        "description": "ATN haulage / land transport operations.",
        "enabled": 1,
        "default_mappings": [_m(cost_center="ATN Haulage")],
        "metrics": [
            "trips_per_month", "avg_lead_time_per_milestone",
            "top5_outsourced_truckers", "returned_billings_count",
            "monthly_haulage_charge_to_file", "monthly_haulage_charge_to_asl",
            "vehicle_maintenance_due",
        ],
    },
    {
        "organization_name": "ATN Domestic Sea",
        "group": "Cost Center",
        "home_module": "Sea Freight",
        "description": "ATN domestic sea operations (Traffic = Domestic).",
        "enabled": 1,
        "default_mappings": [_m(cost_center="ATN Domestic Sea")],
        "metrics": [
            "open_job_files_count", "avg_age_open_jobs", "jobs_handled_count",
            "avg_lead_time_per_milestone", "top5_suppliers",
        ],
    },
    {
        "organization_name": "ATN Warehouse",
        "group": "Cost Center",
        "home_module": "Warehousing",
        "description": "ATN warehouse operations.",
        "enabled": 1,
        "default_mappings": [_m(cost_center="ATN Warehouse")],
        "metrics": [
            "facility_occupancy_pct", "avg_lead_time_per_milestone",
            "handling_in_out_trend", "returned_billings_count",
        ],
    },
    {
        "organization_name": "Vis-Min Branches",
        "group": "Cost Center",
        "home_module": "Job Management",
        "description": "Visayas-Mindanao branch network (cross-module operations).",
        "enabled": 1,
        "default_mappings": [_m(branch="VisMin")],
        "metrics": [
            "open_job_files_count", "avg_age_open_jobs", "jobs_handled_count",
            "avg_lead_time_per_milestone", "returned_billings_count",
            "trips_per_month", "top5_outsourced_truckers",
            "top5_agents_sea_fcl_teu", "top5_agents_sea_lcl_cbm", "top5_agents_air_chw",
            "top5_carriers_sea_fcl_teu", "top5_carriers_sea_lcl_cbm", "top5_carriers_air_chw",
        ],
    },
    {
        "organization_name": "North Luzon Branches",
        "group": "Cost Center",
        "home_module": "Job Management",
        "description": "North Luzon branch network (cross-module operations).",
        "enabled": 1,
        "default_mappings": [_m(branch="North Luzon")],
        "metrics": [
            "open_job_files_count", "avg_age_open_jobs", "jobs_handled_count",
            "avg_lead_time_per_milestone", "returned_billings_count",
            "trips_per_month", "top5_outsourced_truckers",
            "top5_agents_sea_fcl_teu", "top5_agents_sea_lcl_cbm", "top5_agents_air_chw",
            "top5_carriers_sea_fcl_teu", "top5_carriers_sea_lcl_cbm", "top5_carriers_air_chw",
        ],
    },
    {
        "organization_name": "ALTA Fairs & Exhibits (Cost Center)",
        "group": "Cost Center",
        "home_module": "Exhibits",
        "description": "ALTA fairs and exhibits operations view (Cost Center).",
        "enabled": 1,
        "default_mappings": [_m(cost_center="ALTA Fairs & Exhibits")],
        "metrics": [
            "gp_ytd", "gp_prior_ytd", "gp_target", "gp_3year_compare",
            "top10_clients_by_gp", "exhibits_pipeline_list",
        ],
    },
    {
        "organization_name": "ASL Operations",
        "group": "Cost Center",
        "home_module": "Job Management",
        "description": "ASL cross-module operations (Sea / Air / Customs / Transport / Warehouse).",
        "enabled": 1,
        "default_mappings": [_m(cost_center="ASL Operations")],
        "metrics": [
            "open_job_files_count", "avg_age_open_jobs", "jobs_handled_count",
            "avg_lead_time_per_milestone",
            "top5_agents_sea_fcl_teu", "top5_agents_sea_lcl_cbm", "top5_agents_air_chw",
            "top5_carriers_sea_fcl_teu", "top5_carriers_sea_lcl_cbm", "top5_carriers_air_chw",
            "returned_billings_count",
        ],
    },
    # ---------------------------- Resource Centers ----------------------------
    {
        "organization_name": "Human Resources",
        "group": "Resource Center",
        "home_module": "Control Tower",
        "description": "Human Resources function. Sources: HR Vacancy / Turnover / Tardiness OT / Labor Cost trackers.",
        "enabled": 1,
        "default_mappings": [],
        "metrics": [
            "labor_cost_vs_budget", "turnover_rate_trend",
            "open_vacancies_count", "tardiness_ot_trend",
        ],
    },
    {
        "organization_name": "Information Technology",
        "group": "Resource Center",
        "home_module": "Control Tower",
        "description": "Information Technology function. Sources: IT Ticket / Uptime Log / Security Incident trackers.",
        "enabled": 1,
        "default_mappings": [],
        "metrics": [
            "tickets_ytd_count", "avg_ticket_tat",
            "uptime_trend", "security_incidents_count",
        ],
    },
    {
        "organization_name": "Accounting & Finance",
        "group": "Resource Center",
        "home_module": "Accounts",
        "description": "Accounting & Finance function.",
        "enabled": 1,
        "default_mappings": [],
        "metrics": [
            "collections_60plus_aging", "bad_accounts_total",
            "unbilled_shipment_count", "cash_advances_summary",
            "container_deposit_summary", "credit_lines_exposure",
            "investment_holdings_summary", "payables_aging",
            "bank_recon_discrepancies_total", "supplier_cash_bond_total",
        ],
    },
]


def get_organizations():
    """Return the canonical organization registry (copy)."""
    return [dict(o) for o in ORGANIZATIONS]


def get_organization(name):
    """Lookup a single organization spec by name. Returns None if missing."""
    for o in ORGANIZATIONS:
        if o["organization_name"] == name:
            return dict(o)
    return None


def metric_label(metric_key):
    """Display label for a metric key (defaults to the key itself)."""
    return METRICS.get(metric_key, metric_key)
