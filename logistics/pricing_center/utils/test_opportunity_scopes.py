# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Tests for Opportunity Services tab and scope profitability."""

from __future__ import unicode_literals

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt

from logistics.pricing_center.utils.opportunity_scopes import (
	get_customer_service_ytd_profitability,
	on_opportunity_validate,
	populate_virtual_scope_actuals_for_rows,
)


class TestOpportunityServiceScopes(IntegrationTestCase):
	def test_opportunity_services_custom_fields_present(self):
		meta = frappe.get_meta("Opportunity")
		self.assertTrue(meta.has_field("custom_services_tab"))
		self.assertEqual(meta.get_field("custom_services_tab").label, "Services")
		self.assertTrue(meta.has_field("custom_opportunity_scopes"))
		self.assertTrue(meta.has_field("custom_total_scope_opportunity_value"))
		self.assertEqual(
			meta.get_field("custom_total_scope_opportunity_value").label,
			"Total Annual Opportunity Value",
		)

	def test_opportunity_service_scope_child_doctype(self):
		meta = frappe.get_meta("Opportunity Service Scope")
		self.assertTrue(meta.istable)
		for fieldname in (
			"scope_title",
			"service_type",
			"origin_port",
			"destination_port",
			"load_type",
			"air_house_type",
			"sea_house_type",
			"container_no",
			"pick_mode",
			"drop_mode",
			"customs_authority",
			"declaration_type",
			"customs_broker",
			"customs_charge_category",
			"sp_site",
			"sp_manpower",
			"sp_skilled",
			"sp_equipment_type",
			"sp_handling",
			"sp_resource_notes",
			"opportunity_value",
			"actual_revenue",
			"actual_profit",
		):
			self.assertTrue(meta.has_field(fieldname), msg=fieldname)
		self.assertFalse(meta.has_field("sales_quote"))
		self.assertFalse(meta.has_field("job_number"))
		self.assertEqual(meta.get_field("opportunity_value").label, "Annual Opportunity Value")
		self.assertTrue(meta.get_field("actual_revenue").is_virtual)
		self.assertTrue(meta.get_field("actual_profit").is_virtual)

	def test_virtual_actuals_are_not_persisted(self):
		meta = frappe.get_meta("Opportunity Service Scope")
		table_columns = frappe.db.get_table_columns("Opportunity Service Scope")
		self.assertNotIn("actual_revenue", table_columns)
		self.assertNotIn("actual_profit", table_columns)
		self.assertFalse(meta.get_field("actual_revenue").options)
		st = meta.get_field("service_type")
		self.assertEqual(st.options.split("\n")[0], "Air")

	def test_opportunity_with_scopes_serializes_without_error(self):
		company = frappe.db.get_value("Company", {}, "name")
		doc = frappe.get_doc(
			{
				"doctype": "Opportunity",
				"opportunity_from": "Customer",
				"party_name": self._any_customer(),
				"company": company,
				"transaction_date": frappe.utils.today(),
				"custom_opportunity_scopes": [
					{"service_type": "Air", "opportunity_value": 500},
				],
			}
		)
		doc.insert(ignore_permissions=True)
		try:
			payload = frappe.get_doc("Opportunity", doc.name).as_dict()
			self.assertEqual(len(payload.get("custom_opportunity_scopes") or []), 1)
			scope = payload["custom_opportunity_scopes"][0]
			self.assertEqual(scope.get("service_type"), "Air")
			self.assertIn("actual_revenue", scope)
			self.assertIn("actual_profit", scope)
		finally:
			frappe.delete_doc("Opportunity", doc.name, force=1, delete_permanently=True)
			frappe.db.commit()

	def test_scope_totals_roll_up_opportunity_amount(self):
		company = frappe.db.get_value("Company", {}, "name")
		self.assertTrue(company)
		doc = frappe.get_doc(
			{
				"doctype": "Opportunity",
				"opportunity_from": "Customer",
				"party_name": self._any_customer(),
				"company": company,
				"transaction_date": frappe.utils.today(),
				"custom_opportunity_scopes": [
					{
						"service_type": "Air",
						"scope_title": "MNL-HKG",
						"origin_port": self._any_unloco(),
						"destination_port": self._any_unloco(exclude_first=True),
						"opportunity_value": 1000,
					},
					{
						"service_type": "Sea",
						"scope_title": "SIN-LAX",
						"opportunity_value": 2500,
					},
				],
			}
		)
		on_opportunity_validate(doc)
		self.assertEqual(flt(doc.custom_total_scope_opportunity_value), 3500)
		self.assertEqual(flt(doc.opportunity_amount), 3500)

	def test_ytd_actuals_without_customer_zeros(self):
		company = frappe.db.get_value("Company", {}, "name")
		scope_rows = [{"service_type": "Air", "opportunity_value": 500}]
		computed = populate_virtual_scope_actuals_for_rows(scope_rows, company, customer=None)
		self.assertEqual(len(computed), 1)
		self.assertEqual(flt(computed[0]["actual_revenue"]), 0)
		self.assertEqual(flt(computed[0]["actual_profit"]), 0)

	def test_get_customer_service_ytd_profitability_returns_numeric(self):
		company = frappe.db.get_value("Company", {}, "name")
		customer = self._any_customer()
		result = get_customer_service_ytd_profitability(customer, company, "Air")
		self.assertIn("revenue", result)
		self.assertIn("gross_profit", result)
		self.assertGreaterEqual(flt(result["revenue"]), 0)
		self.assertGreaterEqual(flt(result["gross_profit"]), 0)

	def _any_customer(self):
		name = frappe.db.get_value("Customer", {"disabled": 0}, "name")
		if not name:
			self.skipTest("No Customer in site")
		return name

	def _any_unloco(self, exclude_first=False):
		names = frappe.get_all("UNLOCO", filters={"is_active": 1}, pluck="name", limit=2)
		if not names:
			self.skipTest("No UNLOCO in site")
		return names[1] if exclude_first and len(names) > 1 else names[0]
