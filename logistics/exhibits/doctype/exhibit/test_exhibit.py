# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from logistics.exhibits.exhibit_lifecycle import LIFECYCLE_STAGES, get_standard_exhibit_activities


class TestShow(IntegrationTestCase):
	def test_standard_activities_loaded_on_insert(self):
		if not frappe.db.exists("DocType", "Exhibit"):
			self.skipTest("Exhibit DocType not installed")
		doc = frappe.new_doc("Exhibit")
		doc.project_name = "Test Exhibit Details"
		doc.customer = frappe.db.get_value("Customer", {}, "name")
		if not doc.customer:
			self.skipTest("No Customer in system")
		doc.insert(ignore_permissions=True)
		lifecycle_jobs = [r for r in doc.lifecycle_jobs if r.activity_code]
		self.assertEqual(len(lifecycle_jobs), len(get_standard_exhibit_activities()))
		self.assertEqual(doc.lifecycle_stage, "Pre-Show")
		doc.delete(ignore_permissions=True)

	def test_phase_orders_created_on_approval(self):
		if not frappe.db.exists("DocType", "Exhibit"):
			self.skipTest("Exhibit DocType not installed")
		frappe.db.set_single_value("Exhibit Settings", "auto_create_phase_orders", 1)
		doc = frappe.new_doc("Exhibit")
		doc.project_name = "Test Phase Orders"
		doc.customer = frappe.db.get_value("Customer", {}, "name")
		if not doc.customer:
			self.skipTest("No Customer in system")
		doc.insert(ignore_permissions=True)
		doc.status = "Approved"
		doc.save(ignore_permissions=True)
		orders = frappe.get_all(
			"Exhibit Order",
			filters={"exhibit": doc.name},
			pluck="lifecycle_stage",
		)
		for stage in LIFECYCLE_STAGES[:-1]:
			self.assertIn(stage, orders)
		doc.delete(ignore_permissions=True)
