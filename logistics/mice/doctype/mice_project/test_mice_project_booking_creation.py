# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import UnitTestCase
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from logistics.mice.doctype.mice_order.mice_order import action_create_mice_job
from logistics.mice.doctype.mice_project.mice_project_booking_creation import (
	_dialog_creatable_job_type,
	create_booking_or_order_from_exhibit,
	get_exhibit_booking_choices,
)
from logistics.utils.charge_service_type import default_job_type_for_internal_job_service_type


class TestMiceServiceTypeMapping(UnitTestCase):
	def test_mice_maps_to_mice_order(self):
		self.assertEqual(default_job_type_for_internal_job_service_type("MICE"), "MICE Order")
		self.assertEqual(default_job_type_for_internal_job_service_type("Events"), "MICE Order")

	def test_dialog_creatable_job_type_for_mice(self):
		row = frappe._dict(service_type="MICE", job_type="")
		self.assertEqual(_dialog_creatable_job_type(row), "MICE Order")

	def test_dialog_creatable_job_type_for_air_unchanged(self):
		row = frappe._dict(service_type="Air", job_type="")
		self.assertEqual(_dialog_creatable_job_type(row), "Air Booking")


class TestCreateMiceOrderFromExhibit(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("MICE Project not installed")

	def tearDown(self):
		frappe.db.rollback()

	def _site_company(self):
		return frappe.db.get_value("Company", {}, "name")

	def _site_customer(self):
		return frappe.db.get_value("Customer", {"disabled": 0}, "name")

	def _sales_quote_header_defaults(self):
		"""Reuse org/rep fields from an existing submitted quote on this site."""
		fields = [
			"company",
			"customer",
			"shipper",
			"consignee",
			"branch",
			"cost_center",
			"profit_center",
			"quotation_type",
			"naming_series",
			"sales_rep",
			"operations_rep",
			"customer_service_rep",
		]
		row = frappe.db.get_value(
			"Sales Quote",
			{"docstatus": 1, "quotation_type": ("in", ("Regular", "One-off"))},
			fields,
			as_dict=True,
			order_by="modified desc",
		)
		return row or {}

	def _test_site_address(self):
		existing = frappe.db.get_value("Address", {}, "name")
		if existing:
			return existing
		addr = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": f"MICE IJ Test Site {frappe.generate_hash(length=4)}",
				"address_type": "Office",
				"address_line1": "1 Test St",
				"city": "Testville",
			}
		)
		addr.flags.ignore_mandatory = True
		addr.insert(ignore_permissions=True)
		return addr.name

	def _test_item_code(self):
		existing = frappe.db.get_value("Item", {"disabled": 0, "is_sales_item": 1}, "name")
		if existing:
			return existing
		from logistics.air_freight.tests.test_helpers import create_test_item

		return create_test_item(f"MICE IJ Test Item {frappe.generate_hash(length=6)}")

	def _test_organizer(self, customer):
		existing = frappe.db.get_value(
			"MICE Organizer", {"customer": customer}, "name"
		)
		if existing:
			return existing
		org = frappe.new_doc("MICE Organizer")
		org.organizer_name = f"Test Org {frappe.generate_hash(length=4)}"
		org.organizer_type = "Company"
		org.customer = customer
		org.insert(ignore_permissions=True)
		return org.name

	def _minimal_mice_project_with_ij(self):
		company = self._site_company()
		customer = self._site_customer()
		if not company or not customer:
			self.skipTest("Company and Customer required")

		header = self._sales_quote_header_defaults()
		if not header.get("company"):
			header["company"] = company
		if not header.get("customer"):
			header["customer"] = customer

		org = self._test_organizer(customer)
		ex = frappe.new_doc("MICE Project")
		ex.project_name = f"MICE IJ Test {frappe.generate_hash(length=6)}"
		ex.organizer = org
		ex.show_open_date = today()
		ex.show_close_date = add_days(today(), 3)
		ex.company = header.get("company") or company
		ex.insert(ignore_permissions=True)

		sq = frappe.new_doc("Sales Quote")
		sq.update(
			{
				"quotation_type": header.get("quotation_type") or "Regular",
				"naming_series": header.get("naming_series") or "SQU.#########",
				"company": header.get("company") or company,
				"customer": header.get("customer") or customer,
				"date": today(),
				"valid_until": add_days(today(), 30),
				"main_service": "MICE",
				"exhibit": ex.name,
				"exhibit_show_open_date": today(),
				"exhibit_show_close_date": add_days(today(), 3),
				"shipper": header.get("shipper"),
				"consignee": header.get("consignee"),
				"branch": header.get("branch"),
				"cost_center": header.get("cost_center"),
				"profit_center": header.get("profit_center"),
				"sales_rep": header.get("sales_rep"),
				"operations_rep": header.get("operations_rep"),
				"customer_service_rep": header.get("customer_service_rep"),
			}
		)
		sq.append(
			"charges",
			{
				"service_type": "MICE",
				"sp_site": self._test_site_address(),
				"item_code": self._test_item_code(),
				"unit_rate": 100,
			},
		)
		sq.insert(ignore_permissions=True)
		sq.submit()

		ex.append(
			"linked_services",
			{
				"service_type": "MICE",
				"job_description": "Site resource line",
			},
		)
		ex.save(ignore_permissions=True)
		return ex, sq

	def test_booking_choices_include_creatable_mice_order(self):
		ex, _sq = self._minimal_mice_project_with_ij()
		out = get_exhibit_booking_choices(ex.name)
		mice_rows = [
			c
			for c in (out.get("choices") or [])
			if c.get("job_type") == "MICE Order"
		]
		self.assertTrue(mice_rows, out)
		self.assertTrue(mice_rows[0].get("creatable"), mice_rows[0].get("not_creatable_message"))

	def test_create_mice_order_from_internal_job_row(self):
		ex, _sq = self._minimal_mice_project_with_ij()
		ex.reload()
		ij_idx = len(ex.linked_services)

		result = create_booking_or_order_from_exhibit(
			ex.name,
			"MICE Order",
			internal_job_idx=ij_idx,
		)
		self.assertTrue(result.get("mice_order"))
		order_name = result["mice_order"]
		self.assertTrue(frappe.db.exists("MICE Order", order_name))

		ex.reload()
		row = ex.linked_services[ij_idx - 1]
		self.assertEqual(row.job_type, "MICE Order")
		self.assertEqual(row.job_no, order_name)

		order = frappe.get_doc("MICE Order", order_name)
		self.assertEqual(order.exhibit, ex.name)
		self.assertTrue(order.get("charges"))

	def test_mice_order_action_create_mice_job(self):
		ex, _sq = self._minimal_mice_project_with_ij()
		ex.reload()
		result = create_booking_or_order_from_exhibit(
			ex.name,
			"MICE Order",
			internal_job_idx=len(ex.linked_services),
		)
		order_name = result["mice_order"]
		order = frappe.get_doc("MICE Order", order_name)
		order.submit()
		payload = action_create_mice_job(order_name, title="Execution job")
		self.assertTrue(payload.get("created"))
		self.assertTrue(frappe.db.exists("MICE Job", payload["name"]))
		job = frappe.get_doc("MICE Job", payload["name"])
		self.assertEqual(job.exhibit_order, order_name)

		payload2 = action_create_mice_job(order_name, title="Execution job")
		self.assertFalse(payload2.get("created"))
		self.assertTrue(payload2.get("already_exists"))
		self.assertEqual(payload2["name"], payload["name"])
