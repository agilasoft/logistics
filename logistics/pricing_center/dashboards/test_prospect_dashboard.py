# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.pricing_center.dashboards.prospect_dashboard import get_data


class TestProspectDashboard(FrappeTestCase):
	def test_dashboard_uses_correct_link_fieldnames(self):
		data = get_data(frappe._dict())
		self.assertEqual(data.non_standard_fieldnames["Sales Quote"], "prospect")
		self.assertEqual(data.non_standard_fieldnames["Customer"], "prospect_name")
		self.assertEqual(data.non_standard_fieldnames["Opportunity"], "party_name")
		self.assertEqual(data.dynamic_links["party_name"], ["Prospect", "opportunity_from"])

	def test_dashboard_includes_sales_quote_opportunity_customer(self):
		data = get_data(frappe._dict())
		items = []
		for group in data.transactions:
			items.extend(group.get("items") or [])
		for doctype in ("Sales Quote", "Opportunity", "Customer"):
			self.assertIn(doctype, items)
