# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests import UnitTestCase

from logistics.exhibits.exhibit_lifecycle import validate_lifecycle_stage_advance


class TestExhibitLifecycle(UnitTestCase):
	def test_lifecycle_advance_blocked_when_activities_incomplete(self):
		if not frappe.db.exists("DocType", "Exhibit"):
			self.skipTest("Exhibit not installed")
		frappe.db.set_single_value("Exhibit Settings", "strict_lifecycle_mode", 1)
		doc = frappe.new_doc("Exhibit")
		doc.project_name = "Lifecycle Validation Test"
		doc.customer = frappe.db.get_value("Customer", {}, "name")
		if not doc.customer:
			self.skipTest("No Customer")
		doc.insert(ignore_permissions=True)
		doc.reload()
		doc.lifecycle_stage = "Logistics"
		with self.assertRaises(frappe.ValidationError):
			validate_lifecycle_stage_advance(doc)
		doc.delete(ignore_permissions=True)
