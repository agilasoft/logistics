# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestMICEOrganizer(IntegrationTestCase):
	def test_create_minimal_organizer(self):
		doc = frappe.new_doc("MICE Organizer")
		doc.organizer_name = "Test Organizer"
		doc.organizer_type = "Company"
		doc.insert(ignore_permissions=True)
		try:
			self.assertTrue(doc.name)
			self.assertEqual(doc.organizer_name, "Test Organizer")
		finally:
			doc.delete(ignore_permissions=True)

	def test_organizer_name_is_unique(self):
		first = frappe.new_doc("MICE Organizer")
		first.organizer_name = "Dup Organizer"
		first.insert(ignore_permissions=True)

		second = frappe.new_doc("MICE Organizer")
		second.organizer_name = "Dup Organizer"
		try:
			with self.assertRaises(frappe.UniqueValidationError):
				second.insert(ignore_permissions=True)
		finally:
			first.delete(ignore_permissions=True)
