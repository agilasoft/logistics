# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests import UnitTestCase

from logistics.mice.mice_project_lifecycle import validate_lifecycle_stage_advance


class TestExhibitLifecycle(UnitTestCase):
	def test_lifecycle_advance_blocked_when_activities_incomplete(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("Exhibit not installed")
		customer = frappe.db.get_value("Customer", {}, "name")
		if not customer:
			self.skipTest("No Customer")
		organizer_name = "Lifecycle Test Organizer"
		organizer = frappe.db.get_value(
			"MICE Organizer", {"organizer_name": organizer_name}, "name"
		)
		if not organizer:
			org_doc = frappe.new_doc("MICE Organizer")
			org_doc.organizer_name = organizer_name
			org_doc.organizer_type = "Company"
			org_doc.customer = customer
			org_doc.insert(ignore_permissions=True)
			organizer = org_doc.name
		frappe.db.set_single_value("MICE Settings", "strict_lifecycle_mode", 1)
		doc = frappe.new_doc("MICE Project")
		doc.project_name = "Lifecycle Validation Test"
		doc.organizer = organizer
		doc.insert(ignore_permissions=True)
		doc.reload()
		doc.lifecycle_stage = "Logistics"
		with self.assertRaises(frappe.ValidationError):
			validate_lifecycle_stage_advance(doc)
		doc.delete(ignore_permissions=True)
