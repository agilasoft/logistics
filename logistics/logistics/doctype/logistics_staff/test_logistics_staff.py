# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.logistics.doctype.logistics_staff.logistics_staff import (
	ensure_logistics_staff,
	seed_logistics_staff_from_employees_and_links,
)


class TestLogisticsStaff(FrappeTestCase):
	def setUp(self):
		self.employee = frappe.db.get_value("Employee", {"status": "Active"}, "name") or frappe.db.get_value(
			"Employee", {}, "name"
		)

	def tearDown(self):
		frappe.db.rollback()

	def test_doctype_links_rep_fields_to_logistics_staff(self):
		sales_quote = frappe.get_meta("Sales Quote")
		for fieldname in ("sales_rep", "operations_rep", "customer_service_rep"):
			field = sales_quote.get_field(fieldname)
			self.assertEqual(field.options, "Logistics Staff")
			self.assertIn("Logistics Staff", field.link_filters)
			self.assertIn(fieldname, field.link_filters)

		warehouseman = frappe.get_meta("Warehouse Job Operations").get_field("employee")
		self.assertEqual(warehouseman.label, "Warehouseman")
		self.assertEqual(warehouseman.options, "Logistics Staff")
		self.assertIn("warehouseman", warehouseman.link_filters)

		unchanged = frappe.get_meta("Change Request").get_field("dispatcher")
		self.assertEqual(unchanged.options, "Employee")

	def test_requires_a_role(self):
		if not self.employee:
			self.skipTest("No Employee to link")
		existing = frappe.db.get_value("Logistics Staff", {"employee": self.employee}, "name")
		if existing:
			frappe.delete_doc("Logistics Staff", existing, force=True, ignore_permissions=True)
		doc = frappe.new_doc("Logistics Staff")
		doc.employee = self.employee
		with self.assertRaises(frappe.ValidationError):
			doc.insert(ignore_permissions=True)

	def test_ensure_creates_staff_named_for_the_employee(self):
		if not self.employee:
			self.skipTest("No Employee to link")
		name = ensure_logistics_staff(self.employee, sales_rep=1, operations_rep=0, customer_service_rep=0)
		self.assertEqual(name, self.employee)
		doc = frappe.get_doc("Logistics Staff", name)
		self.assertEqual(doc.employee, self.employee)
		self.assertEqual(doc.sales_rep, 1)
		self.assertEqual(doc.operations_rep, 0)
		self.assertTrue(doc.employee_name)

		again = ensure_logistics_staff(self.employee, operations_rep=1, customer_service_rep=1)
		self.assertEqual(again, name)
		doc.reload()
		self.assertEqual(doc.sales_rep, 1)
		self.assertEqual(doc.operations_rep, 1)
		self.assertEqual(doc.customer_service_rep, 1)

	def test_seed_is_idempotent_for_flagged_employees(self):
		if not self.employee:
			self.skipTest("No Employee to link")
		if frappe.db.has_column("Employee", "custom_sales_rep"):
			frappe.db.set_value("Employee", self.employee, "custom_sales_rep", 1, update_modified=False)
		else:
			ensure_logistics_staff(self.employee, sales_rep=1, operations_rep=0, customer_service_rep=0)
		first = seed_logistics_staff_from_employees_and_links()
		second = seed_logistics_staff_from_employees_and_links()
		self.assertGreaterEqual(first, 1)
		self.assertGreaterEqual(second, 1)
		self.assertTrue(frappe.db.exists("Logistics Staff", {"employee": self.employee, "sales_rep": 1}))
