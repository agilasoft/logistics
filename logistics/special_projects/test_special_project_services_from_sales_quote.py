# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Tests for copying Sales Quote programme data onto Special Project."""

from __future__ import annotations

import frappe
from frappe.tests import IntegrationTestCase

from logistics.special_projects.special_project_services_from_sales_quote import (
	copy_special_project_programme_data_from_sales_quote,
	linked_services_view_rows_for_sales_quote,
)
from logistics.special_projects.test_special_project_helpers import (
	new_special_project_for_test,
)
from logistics.utils.linked_service_compat import linked_service_doctype
from logistics.utils.sales_quote_programme_charges import (
	map_sales_quote_charge_to_programme_charge_dict,
)


class TestSpecialProjectServicesFromSalesQuote(IntegrationTestCase):
	def _cleanup_special_project(self, sp_name: str) -> None:
		if not sp_name or not frappe.db.exists("Special Project", sp_name):
			return
		project = frappe.db.get_value("Special Project", sp_name, "project")
		frappe.delete_doc("Special Project", sp_name, force=True, ignore_permissions=True)
		if project and frappe.db.exists("Project", project):
			try:
				frappe.delete_doc("Project", project, force=True, ignore_permissions=True)
			except Exception:
				pass

	def _cleanup_sales_quote(self, sq_name: str) -> None:
		if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
			return
		frappe.delete_doc("Sales Quote", sq_name, force=True, ignore_permissions=True)

	def test_map_charge_preserves_linked_service_for_special_project(self):
		mapped = map_sales_quote_charge_to_programme_charge_dict(
			{
				"service_type": "Air",
				"item_code": "FREIGHT",
				"charge_scope": "Linked",
				"linked_service": "IJ-TEST",
			},
			"SQ-TEST",
			"Special Project Charges",
		)
		self.assertEqual(mapped.get("linked_service"), "IJ-TEST")
		self.assertEqual(mapped.get("charge_scope"), "Linked")

	def test_copy_charges_from_quote_preserves_linked_service(self):
		if not frappe.db.exists("DocType", linked_service_doctype()):
			self.skipTest("Linked Service not installed")

		sp = new_special_project_for_test("SP SQ Services")
		if not sp:
			self.skipTest("Company, Customer, and Cost Center required")

		company = sp.company
		customer = sp.customer
		sq = frappe.new_doc("Sales Quote")
		sq.quotation_type = "Project"
		sq.main_service = "Special Project"
		sq.naming_series = "PQ.#####"
		sq.company = company
		sq.customer = customer
		sq.shipper = frappe.db.get_value("Shipper", {}, "name")
		sq.consignee = frappe.db.get_value("Consignee", {}, "name")
		sq.valid_till = frappe.utils.add_days(frappe.utils.today(), 30)
		sq.flags.ignore_mandatory = True
		sq.insert(ignore_permissions=True)

		ls_air = frappe.new_doc(linked_service_doctype())
		ls_air.service_type = "Air"
		ls_air.parent_booking_type = "Sales Quote"
		ls_air.parent_booking_name = sq.name
		ls_air.flags.ignore_permissions = True
		ls_air.insert(ignore_permissions=True)

		ls_sea = frappe.new_doc(linked_service_doctype())
		ls_sea.service_type = "Sea"
		ls_sea.parent_booking_type = "Sales Quote"
		ls_sea.parent_booking_name = sq.name
		ls_sea.flags.ignore_permissions = True
		ls_sea.insert(ignore_permissions=True)

		sq.append(
			"charges",
			{
				"service_type": "Air",
				"item_code": "FREIGHT",
				"charge_scope": "Linked",
				"linked_service": ls_air.name,
				"unit_rate": 100,
			},
		)
		sq.append(
			"charges",
			{
				"service_type": "Sea",
				"item_code": "FREIGHT",
				"charge_scope": "Linked",
				"linked_service": ls_sea.name,
				"unit_rate": 200,
			},
		)
		sq.append(
			"charges",
			{
				"service_type": "Special Project",
				"item_code": "SP-PM-FEE",
				"charge_scope": "Main",
				"unit_rate": 50,
			},
		)
		sq.flags.ignore_mandatory = True
		sq.save(ignore_permissions=True)
		sq.submit()

		sp.sales_quote = sq.name
		sp.status = "Draft"
		sp.flags.ignore_mandatory = True
		sp.insert(ignore_permissions=True)

		try:
			copy_special_project_programme_data_from_sales_quote(
				sp, sq.name, clear_existing=True
			)
			self.assertEqual(len(sp.charges), 3)

			linked_charges = [c for c in sp.charges if (c.charge_scope or "").strip() == "Linked"]
			self.assertEqual(len(linked_charges), 2)
			linked_by_service = {c.linked_service: c for c in linked_charges}
			self.assertEqual(linked_by_service[ls_air.name].item_code, "FREIGHT")
			self.assertEqual(linked_by_service[ls_sea.name].item_code, "FREIGHT")

			view_rows = linked_services_view_rows_for_sales_quote(sq.name)
			self.assertEqual(len(view_rows), 2)

			sp.flags.ignore_links = True
			sp.flags.ignore_mandatory = True
			sp.save(ignore_permissions=True)

			reloaded = frappe.get_doc("Special Project", sp.name)
			self.assertEqual(len(reloaded.charges), 3)
			for charge in reloaded.charges:
				if (charge.charge_scope or "").strip() == "Linked":
					self.assertTrue(charge.linked_service)
					self.assertIn(
						charge.linked_service,
						{ls_air.name, ls_sea.name},
					)
		finally:
			self._cleanup_special_project(sp.name)
			self._cleanup_sales_quote(sq.name)

	def test_copy_preserves_distinct_linked_services_for_duplicate_service_types(self):
		if not frappe.db.exists("DocType", linked_service_doctype()):
			self.skipTest("Linked Service not installed")

		sp = new_special_project_for_test("SP SQ Dup Air")
		if not sp:
			self.skipTest("Company, Customer, and Cost Center required")

		company = sp.company
		customer = sp.customer
		sq = frappe.new_doc("Sales Quote")
		sq.quotation_type = "Project"
		sq.main_service = "Special Project"
		sq.naming_series = "PQ.#####"
		sq.company = company
		sq.customer = customer
		sq.shipper = frappe.db.get_value("Shipper", {}, "name")
		sq.consignee = frappe.db.get_value("Consignee", {}, "name")
		sq.valid_till = frappe.utils.add_days(frappe.utils.today(), 30)
		sq.flags.ignore_mandatory = True
		sq.insert(ignore_permissions=True)

		ls_air_a = frappe.new_doc(linked_service_doctype())
		ls_air_a.service_type = "Air"
		ls_air_a.parent_booking_type = "Sales Quote"
		ls_air_a.parent_booking_name = sq.name
		ls_air_a.flags.ignore_permissions = True
		ls_air_a.insert(ignore_permissions=True)

		ls_air_b = frappe.new_doc(linked_service_doctype())
		ls_air_b.service_type = "Air"
		ls_air_b.parent_booking_type = "Sales Quote"
		ls_air_b.parent_booking_name = sq.name
		ls_air_b.flags.ignore_permissions = True
		ls_air_b.insert(ignore_permissions=True)

		sq.append(
			"charges",
			{
				"service_type": "Air",
				"item_code": "FREIGHT-A",
				"charge_scope": "Linked",
				"linked_service": ls_air_a.name,
				"unit_rate": 100,
			},
		)
		sq.append(
			"charges",
			{
				"service_type": "Air",
				"item_code": "FREIGHT-B",
				"charge_scope": "Linked",
				"linked_service": ls_air_b.name,
				"unit_rate": 150,
			},
		)
		sq.flags.ignore_mandatory = True
		sq.save(ignore_permissions=True)
		sq.submit()

		sp.sales_quote = sq.name
		sp.status = "Draft"
		sp.flags.ignore_mandatory = True
		sp.insert(ignore_permissions=True)

		try:
			copy_special_project_programme_data_from_sales_quote(
				sp, sq.name, clear_existing=True
			)
			by_item = {c.item_code: c for c in sp.charges}
			self.assertEqual(by_item["FREIGHT-A"].linked_service, ls_air_a.name)
			self.assertEqual(by_item["FREIGHT-B"].linked_service, ls_air_b.name)
		finally:
			self._cleanup_special_project(sp.name)
			self._cleanup_sales_quote(sq.name)
