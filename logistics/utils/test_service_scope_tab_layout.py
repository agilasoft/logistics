# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Tests for Sales Quote Service Scope tab field layout."""

from __future__ import unicode_literals

import frappe
from frappe.tests import IntegrationTestCase


class TestServiceScopeTabLayout(IntegrationTestCase):
	def test_service_scope_tab_fields_present(self):
		meta = frappe.get_meta("Sales Quote")
		self.assertTrue(meta.has_field("service_scope_tab"))
		self.assertEqual(meta.get_field("service_scope_tab").label, "Scope")
		self.assertTrue(meta.has_field("routing_tab"))
		self.assertTrue(meta.has_field("services_tab"))
		self.assertTrue(meta.has_field("charges_tab"))
		self.assertTrue(meta.has_field("scope_title"))
		self.assertTrue(meta.has_field("incoterm_place"))
		self.assertTrue(meta.has_field("main_service"))
		self.assertTrue(meta.has_field("one_off_params_section"))
		self.assertEqual(meta.get_field("one_off_params_section").label, "Main Service Parameters")
		ls_field = "linked_services" if meta.has_field("linked_services") else "internal_job_details"
		self.assertTrue(meta.has_field(ls_field))
		self.assertTrue(meta.has_field("sales_quote_pack"))

	def test_scope_params_visible_for_regular_and_one_off(self):
		meta = frappe.get_meta("Sales Quote")
		params = meta.get_field("one_off_params_section")
		self.assertIn("Regular", params.depends_on)
		self.assertIn("One-off", params.depends_on)
		meta = frappe.get_meta("Sales Quote")
		order = [f.fieldname for f in meta.fields]
		scope_idx = order.index("service_scope_tab")
		params_idx = order.index("one_off_params_section")
		routing_idx = order.index("routing_tab")
		services_idx = order.index("services_tab")
		charges_idx = order.index("charges_tab")
		self.assertLess(scope_idx, params_idx)
		self.assertLess(params_idx, routing_idx)
		self.assertLess(routing_idx, services_idx)
		self.assertLess(services_idx, charges_idx)

	def test_sales_quote_charge_linked_scope_options(self):
		meta = frappe.get_meta("Sales Quote Charge")
		df = meta.get_field("charge_scope")
		self.assertIn("Linked", df.options)
		self.assertFalse(meta.has_field("service_scope"))
		link_field = "linked_service" if meta.has_field("linked_service") else "internal_job"
		self.assertTrue(meta.has_field(link_field))
