# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.pricing_center.crm_sales_quote import (
	make_sales_quote_from_lead,
	make_sales_quote_from_prospect,
)
from logistics.pricing_center.doctype.pricing_center_settings.pricing_center_settings import (
	get_crm_sales_quote_settings,
)


class TestCrmSalesQuote(FrappeTestCase):
	def setUp(self):
		self.company = frappe.db.get_value("Company", {}, "name")
		if not self.company:
			self.skipTest("No Company available for CRM Sales Quote tests")
		self._ensure_pricing_center_settings()

	def tearDown(self):
		frappe.db.rollback()

	def _ensure_pricing_center_settings(self):
		if frappe.db.exists("Pricing Center Settings", {"company": self.company}):
			return
		frappe.get_doc(
			{
				"doctype": "Pricing Center Settings",
				"company": self.company,
				"valid_until_offset_days": 30,
			}
		).insert(ignore_permissions=True)

	def _set_crm_settings(self, **kwargs):
		doc = frappe.get_doc("Pricing Center Settings", {"company": self.company})
		for key, value in kwargs.items():
			setattr(doc, key, value)
		doc.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Pricing Center Settings")

	def _make_lead(self, suffix):
		lead = frappe.get_doc(
			{
				"doctype": "Lead",
				"lead_name": f"CRM SQ Lead {suffix}",
				"company_name": f"CRM SQ Lead Co {suffix}",
				"company": self.company,
			}
		)
		lead.insert(ignore_permissions=True)
		return lead.name

	def _make_prospect(self, suffix):
		prospect = frappe.get_doc(
			{
				"doctype": "Prospect",
				"company_name": f"CRM SQ Prospect {suffix}",
				"company": self.company,
			}
		)
		prospect.insert(ignore_permissions=True)
		return prospect.name

	def test_settings_default_disabled(self):
		self._set_crm_settings(allow_sales_quote_from_lead=0, allow_sales_quote_from_prospect=0)
		settings = get_crm_sales_quote_settings(self.company)
		self.assertFalse(settings.allow_sales_quote_from_lead)
		self.assertFalse(settings.allow_sales_quote_from_prospect)

	def test_lead_sales_quote_blocked_when_setting_disabled(self):
		self._set_crm_settings(allow_sales_quote_from_lead=0)
		lead_name = self._make_lead("blocked")
		with self.assertRaises(frappe.ValidationError):
			make_sales_quote_from_lead(lead_name)

	def test_lead_sales_quote_allowed_when_setting_enabled(self):
		self._set_crm_settings(allow_sales_quote_from_lead=1)
		lead_name = self._make_lead("allowed")
		sq = make_sales_quote_from_lead(lead_name)
		self.assertEqual(sq.customer, frappe.db.get_value("Customer", {"lead_name": lead_name}, "name"))
		self.assertEqual(sq.lead, lead_name)

	def test_prospect_sales_quote_allowed_when_setting_enabled(self):
		self._set_crm_settings(allow_sales_quote_from_prospect=1)
		prospect_name = self._make_prospect("allowed")
		sq = make_sales_quote_from_prospect(prospect_name)
		self.assertEqual(
			sq.customer,
			frappe.db.get_value("Customer", {"prospect_name": prospect_name}, "name"),
		)
		if sq.meta.get_field("prospect"):
			self.assertEqual(sq.prospect, prospect_name)

	def test_prospect_sales_quote_blocked_when_setting_disabled(self):
		self._set_crm_settings(allow_sales_quote_from_prospect=0)
		prospect_name = self._make_prospect("blocked")
		with self.assertRaises(frappe.ValidationError):
			make_sales_quote_from_prospect(prospect_name)
