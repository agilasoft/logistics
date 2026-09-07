# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

from frappe.tests import UnitTestCase

import frappe

from logistics.logistics.page.role_permission_matrix.role_permission_matrix import (
	get_doctypes_for_module,
	get_filter_options,
	get_matrix,
)

TEST_ROLE = "_Test RPM Matrix Role"


class TestRolePermissionMatrix(UnitTestCase):
	def tearDown(self):
		if frappe.db.exists("Role", TEST_ROLE):
			frappe.delete_doc("Role", TEST_ROLE, force=True, ignore_permissions=True)
		frappe.db.rollback()

	def _ensure_role(self):
		if frappe.db.exists("Role", TEST_ROLE):
			return
		frappe.get_doc(
			{"doctype": "Role", "role_name": TEST_ROLE, "desk_access": 1}
		).insert(ignore_permissions=True)

	def test_get_matrix_empty_without_role(self):
		self.assertEqual(get_matrix(None), [])
		self.assertEqual(get_matrix(""), [])

	def test_new_role_has_no_rows_until_module_filter(self):
		self._ensure_role()
		self.assertEqual(get_matrix(role=TEST_ROLE), [])

	def test_module_filter_adds_placeholders(self):
		self._ensure_role()
		rows = get_matrix(role=TEST_ROLE, module="Air Freight")
		self.assertTrue(rows)
		self.assertTrue(any(r.get("parent") == "Air Booking" for r in rows))
		self.assertTrue(all(r.get("_is_placeholder") for r in rows))
		self.assertFalse(any(r.get("parent") == "DocType" for r in rows))

	def test_get_doctypes_for_module(self):
		names = get_doctypes_for_module("Air Freight")
		self.assertIn("Air Booking", names)
		self.assertNotIn("DocType", names)

	def test_get_filter_options_shape(self):
		data = get_filter_options()
		self.assertIn("roles", data)
		self.assertIn("doctypes", data)
		self.assertIn("modules", data)
		module_values = [m.get("value") for m in data["modules"]]
		self.assertIn("Air Freight", module_values)
		self.assertIn("Logistics", module_values)
