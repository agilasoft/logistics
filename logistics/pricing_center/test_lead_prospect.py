# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.pricing_center.lead_prospect import populate_annual_revenue_from_leads


class TestLeadProspectAnnualRevenue(FrappeTestCase):
	def setUp(self):
		self.company = frappe.db.get_value("Company", {}, "name")
		if not self.company:
			self.skipTest("No Company available")

	def tearDown(self):
		frappe.db.rollback()

	def _make_lead(self, suffix, annual_revenue=None):
		lead = frappe.get_doc(
			{
				"doctype": "Lead",
				"lead_name": f"Revenue Lead {suffix}",
				"company_name": f"Revenue Lead Co {suffix}",
				"company": self.company,
				"annual_revenue": annual_revenue,
			}
		)
		lead.insert(ignore_permissions=True)
		return lead

	def test_new_prospect_copies_annual_revenue_from_lead(self):
		suffix = frappe.generate_hash(length=6)
		lead = self._make_lead(suffix, 2500000)
		prospect = frappe.get_doc(
			{
				"doctype": "Prospect",
				"company_name": f"Revenue Prospect {suffix}",
				"company": self.company,
				"leads": [{"lead": lead.name}],
			}
		)
		prospect.insert(ignore_permissions=True)
		prospect.reload()
		self.assertEqual(prospect.annual_revenue, 2500000)

	def test_existing_revenue_is_not_overwritten(self):
		suffix = frappe.generate_hash(length=6)
		lead = self._make_lead(suffix, 2500000)
		prospect = frappe.get_doc(
			{
				"doctype": "Prospect",
				"company_name": f"Revenue Prospect Keep {suffix}",
				"company": self.company,
				"annual_revenue": 100,
				"leads": [{"lead": lead.name}],
			}
		)
		prospect.insert(ignore_permissions=True)
		prospect.reload()
		self.assertEqual(prospect.annual_revenue, 100)

	def test_add_lead_fills_empty_prospect_revenue(self):
		suffix = frappe.generate_hash(length=6)
		lead = self._make_lead(suffix, 875000)
		prospect = frappe.get_doc(
			{
				"doctype": "Prospect",
				"company_name": f"Revenue Prospect Add {suffix}",
				"company": self.company,
			}
		)
		prospect.insert(ignore_permissions=True)
		prospect.reload()
		self.assertFalse(prospect.annual_revenue)

		prospect.append("leads", {"lead": lead.name})
		populate_annual_revenue_from_leads(prospect)
		self.assertEqual(prospect.annual_revenue, 875000)

	def test_cleared_revenue_is_not_refilled_from_existing_leads(self):
		suffix = frappe.generate_hash(length=6)
		lead = self._make_lead(suffix, 2500000)
		prospect = frappe.get_doc(
			{
				"doctype": "Prospect",
				"company_name": f"Revenue Prospect Clear {suffix}",
				"company": self.company,
				"annual_revenue": 2500000,
				"leads": [{"lead": lead.name}],
			}
		)
		prospect.insert(ignore_permissions=True)
		prospect.reload()
		prospect.annual_revenue = 0
		populate_annual_revenue_from_leads(prospect)
		self.assertFalse(prospect.annual_revenue)
