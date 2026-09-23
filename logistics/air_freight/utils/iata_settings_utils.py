# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

from __future__ import unicode_literals

import frappe

PUBLIC_SETTINGS_FIELDS = (
	"cargo_xml_enabled",
	"connection_mode",
	"ccs_provider",
	"dg_autocheck_enabled",
	"cass_enabled",
	"tact_subscription",
	"net_rates_enabled",
	"track_trace_enabled",
	"epic_enabled",
	"test_mode",
	"test_endpoint",
	"debug_logging",
)


def _has_company_field():
	return frappe.db.has_column("IATA Settings", "company")


def resolve_company(company=None, master_awb=None, air_shipment=None):
	"""Resolve the company whose IATA Settings should apply."""
	if company:
		return company

	if air_shipment:
		shipment_company = frappe.db.get_value("Air Shipment", air_shipment, "company")
		if shipment_company:
			return shipment_company

	if master_awb:
		shipment_company = frappe.db.get_value(
			"Air Shipment",
			{"master_awb": master_awb},
			"company",
		)
		if shipment_company:
			return shipment_company

	return (
		frappe.defaults.get_user_default("Company")
		or frappe.db.get_single_value("Global Defaults", "default_company")
	)


def _resolve_settings_name(company=None):
	"""Return the IATA Settings document name for a company (or legacy fallback)."""
	if company and frappe.db.exists("IATA Settings", company):
		return company

	if _has_company_field() and company:
		settings_name = frappe.db.get_value(
			"IATA Settings",
			{"company": company},
			"name",
		)
		if settings_name:
			return settings_name

	# Legacy schema before company column / per-company migration
	if frappe.db.exists("IATA Settings", "IATA Settings"):
		return "IATA Settings"

	return frappe.db.get_value(
		"IATA Settings",
		{},
		"name",
		order_by="modified desc",
	)


def get_settings(company=None, master_awb=None, air_shipment=None):
	"""Get IATA Settings document for a company."""
	company = resolve_company(
		company=company,
		master_awb=master_awb,
		air_shipment=air_shipment,
	)
	settings_name = _resolve_settings_name(company)
	if not settings_name:
		return None

	frappe.flags.ignore_permissions = True
	try:
		return frappe.get_doc("IATA Settings", settings_name)
	finally:
		frappe.flags.ignore_permissions = False


def default_settings():
	return frappe._dict(
		test_mode=0,
		test_endpoint=None,
		cargo_xml_enabled=0,
		cargo_xml_endpoint=None,
		cargo_xml_username=None,
		connection_mode="Direct",
		ccs_provider=None,
		ccs_participant_code=None,
		ccs_endpoint=None,
		ccs_test_endpoint=None,
		dg_autocheck_enabled=0,
		cass_enabled=0,
		cass_role="Agent",
		cass_country=None,
		cass_participant_code=None,
		cass_charge_item=None,
		cass_api_endpoint=None,
		cass_iinet_host=None,
		tact_subscription=0,
		net_rates_enabled=0,
		track_trace_enabled=0,
		epic_enabled=0,
		debug_logging=0,
	)


def get_public_settings(company=None, master_awb=None, air_shipment=None):
	"""Non-sensitive flags readable without IATA Settings DocType permission."""
	company = resolve_company(
		company=company,
		master_awb=master_awb,
		air_shipment=air_shipment,
	)
	settings_name = _resolve_settings_name(company)
	if not settings_name:
		return default_settings()

	settings = frappe._dict()
	for fieldname in PUBLIC_SETTINGS_FIELDS:
		settings[fieldname] = frappe.db.get_value(
			"IATA Settings", settings_name, fieldname
		)
	return settings
