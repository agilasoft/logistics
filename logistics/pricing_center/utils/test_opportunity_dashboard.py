# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Tests for Opportunity dashboard payload."""

from __future__ import unicode_literals

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt

from logistics.pricing_center.utils.opportunity_dashboard import (
	build_opportunity_dashboard_payload,
	get_default_dashboard_metric,
)


class TestOpportunityDashboard(IntegrationTestCase):
	def test_crm_settings_default_metric_field(self):
		if not frappe.db.exists("DocType", "CRM Settings"):
			self.skipTest("CRM Settings not installed")
		meta = frappe.get_meta("CRM Settings")
		self.assertTrue(meta.has_field("custom_opportunity_dashboard_default_metric"))
		self.assertIn(get_default_dashboard_metric(), ("Revenue", "Profit"))

	def test_opportunity_dashboard_tab_fields(self):
		meta = frappe.get_meta("Opportunity")
		self.assertTrue(meta.has_field("custom_dashboard_tab"))
		self.assertEqual(meta.get_field("custom_dashboard_tab").label, "Dashboard")
		self.assertTrue(meta.has_field("custom_opportunity_misc_tab"))
		self.assertTrue(meta.has_field("custom_opportunity_dashboard_html"))
		html_field = meta.get_field("custom_opportunity_dashboard_html")
		self.assertFalse(html_field.hidden)
		fields = [f.fieldname for f in meta.fields]
		self.assertLess(
			fields.index("custom_total_scope_actual_profit"),
			fields.index("custom_opportunity_misc_tab"),
		)
		self.assertLess(fields.index("custom_opportunity_misc_tab"), fields.index("utm_analytics_section"))
		self.assertLess(fields.index("dashboard_tab"), fields.index("custom_dashboard_tab"))
		self.assertLess(fields.index("open_activities_html"), fields.index("custom_dashboard_tab"))

	def test_dashboard_payload_structure(self):
		company = frappe.db.get_value("Company", {}, "name")
		customer = frappe.db.get_value("Customer", {"disabled": 0}, "name")
		if not customer:
			self.skipTest("No Customer in site")
		doc = frappe.get_doc(
			{
				"doctype": "Opportunity",
				"opportunity_from": "Customer",
				"party_name": customer,
				"company": company,
				"transaction_date": frappe.utils.today(),
				"custom_opportunity_scopes": [
					{
						"service_type": "Air",
						"scope_title": "Lane A",
						"opportunity_value": 100000,
						"origin_port": "PHMNL",
						"destination_port": "USLAX",
						"load_type": frappe.db.get_value("Load Type", {}, "name"),
					},
					{"service_type": "Sea", "scope_title": "Lane B", "opportunity_value": 200000},
				],
			}
		)
		payload = build_opportunity_dashboard_payload(doc)
		self.assertTrue(payload["has_scopes"])
		self.assertEqual(flt(payload["overall"]["target"]), 300000)
		self.assertEqual(len(payload["services"]), 2)
		self.assertEqual(len(payload["scopes"]), 2)
		air_scope = next(s for s in payload["scopes"] if s["service_type"] == "Air")
		self.assertEqual(air_scope["origin"], "PHMNL")
		self.assertEqual(air_scope["destination"], "USLAX")
		self.assertTrue(air_scope.get("load_type"))
		for scope in payload["scopes"]:
			self.assertIn("origin", scope)
			self.assertIn("destination", scope)
			self.assertIn("load_type", scope)
		for svc in payload["services"]:
			self.assertIn("revenue_attainment_pct", svc)
			self.assertIn("profit_attainment_pct", svc)

	def test_dashboard_html_renders(self):
		from logistics.pricing_center.api.opportunity_dashboard import get_opportunity_dashboard_html
		from logistics.pricing_center.utils.opportunity_dashboard import render_opportunity_dashboard_html

		company = frappe.db.get_value("Company", {}, "name")
		customer = frappe.db.get_value("Customer", {"disabled": 0}, "name")
		if not customer:
			self.skipTest("No Customer in site")
		doc = frappe.get_doc(
			{
				"doctype": "Opportunity",
				"opportunity_from": "Customer",
				"party_name": customer,
				"company": company,
				"transaction_date": frappe.utils.today(),
				"custom_opportunity_scopes": [
					{
						"service_type": "Air",
						"scope_title": "Lane A",
						"opportunity_value": 100000,
						"origin_port": "PHMNL",
						"destination_port": "USLAX",
					},
				],
			}
		)
		payload = build_opportunity_dashboard_payload(doc)
		html = render_opportunity_dashboard_html(payload, "Revenue")
		self.assertIn("log-opp-dash", html)
		self.assertIn("Opportunity Value Attainment", html)
		self.assertIn("Lane A", html)
		self.assertIn("PHMNL", html)
		self.assertIn("USLAX", html)
		self.assertIn("Scope / Services Detail", html)

		opp = frappe.db.get_value("Opportunity", {}, "name")
		if opp:
			api_html = get_opportunity_dashboard_html(opportunity=opp, metric="Revenue")
			self.assertIn("log-opp-dash", api_html or "")

	def test_scope_list_view_lane_fields(self):
		meta = frappe.get_meta("Opportunity Service Scope")
		for fn in ("origin_port", "destination_port", "load_type"):
			field = meta.get_field(fn)
			self.assertTrue(field.in_list_view, fn)
		self.assertEqual(meta.get_field("origin_port").label, "Origin")
		self.assertEqual(meta.get_field("destination_port").label, "Destination")
		self.assertEqual(meta.get_field("location_from").label, "Origin")
		self.assertEqual(meta.get_field("location_to").label, "Destination")

	def test_scope_parameters_section_is_collapsible(self):
		meta = frappe.get_meta("Opportunity Service Scope")
		section = meta.get_field("section_break_lane")
		self.assertTrue(section.collapsible)
