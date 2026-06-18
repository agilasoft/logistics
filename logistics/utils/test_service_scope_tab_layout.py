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
		self.assertTrue(meta.has_field("scope_title"))
		self.assertTrue(meta.has_field("incoterm_place"))
		self.assertTrue(meta.has_field("main_service"))
		ls_field = "linked_services" if meta.has_field("linked_services") else "internal_job_details"
		self.assertTrue(meta.has_field(ls_field))
		self.assertTrue(meta.has_field("sales_quote_pack"))

	def test_sales_quote_charge_linked_scope_options(self):
		meta = frappe.get_meta("Sales Quote Charge")
		df = meta.get_field("charge_scope")
		self.assertIn("Linked", df.options)
		self.assertTrue(meta.has_field("service_scope"))
		link_field = "linked_service" if meta.has_field("linked_service") else "internal_job"
		self.assertTrue(meta.has_field(link_field))
