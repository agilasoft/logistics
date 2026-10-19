# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Roles listed on Logistics Settings can save document list columns."""

from __future__ import annotations

import frappe
from frappe.tests import IntegrationTestCase

from logistics.desk.list_settings import (
	extend_bootinfo,
	save_listview_settings,
	user_has_list_settings_role,
)


class TestListSettingsRole(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.role = f"List Settings {frappe.generate_hash(length=6)}"
		self.other_role = f"No List Settings {frappe.generate_hash(length=6)}"
		frappe.get_doc({"doctype": "Role", "role_name": self.role}).insert(ignore_permissions=True)
		frappe.get_doc({"doctype": "Role", "role_name": self.other_role}).insert(ignore_permissions=True)
		self.editor = self._user(self.role)
		self.outsider = self._user(self.other_role)
		self.settings = frappe.get_single("Logistics Settings")
		self._original_roles = [
			row.role for row in (self.settings.get("list_settings_roles") or []) if row.role
		]
		self.settings.append("list_settings_roles", {"role": self.role})
		self.settings.save(ignore_permissions=True)
		self._list_existed = bool(frappe.db.exists("List View Settings", "ToDo"))
		self._previous_fields = frappe.db.get_value("List View Settings", "ToDo", "fields")
		self._previous_count = frappe.db.get_value("List View Settings", "ToDo", "disable_count")
		self._setters = {
			row.name: row.value
			for row in frappe.get_all(
				"Property Setter",
				filters={"doc_type": "ToDo", "property": "in_list_view"},
				fields=["name", "value"],
			)
		}

	def tearDown(self):
		frappe.set_user("Administrator")
		settings = frappe.get_single("Logistics Settings")
		settings.set(
			"list_settings_roles",
			[{"role": role} for role in self._original_roles],
		)
		settings.save(ignore_permissions=True)
		self._restore_todo_list()
		super().tearDown()

	def test_listed_role_can_save_list_settings(self):
		frappe.set_user(self.editor)
		self.assertTrue(user_has_list_settings_role())
		boot = frappe._dict()
		extend_bootinfo(boot)
		self.assertTrue(boot.can_edit_list_settings)

		result = save_listview_settings(
			"ToDo",
			{"disable_count": 1, "fields": [{"fieldname": "status", "label": "Status"}]},
			["priority"],
		)
		self.assertEqual(result["listview_settings"].disable_count, 1)
		self.assertEqual(frappe.db.get_value("List View Settings", "ToDo", "disable_count"), 1)
		setter = frappe.db.get_value(
			"Property Setter",
			{"doc_type": "ToDo", "field_name": "status", "property": "in_list_view"},
			"value",
		)
		self.assertEqual(str(setter), "1")

	def test_other_role_cannot_save_list_settings(self):
		frappe.set_user(self.outsider)
		self.assertFalse(user_has_list_settings_role())
		boot = frappe._dict()
		extend_bootinfo(boot)
		self.assertFalse(boot.can_edit_list_settings)
		with self.assertRaises(frappe.PermissionError):
			save_listview_settings("ToDo", {"disable_count": 0}, [])

	def test_unknown_column_is_rejected(self):
		frappe.set_user(self.editor)
		with self.assertRaises(frappe.ValidationError):
			save_listview_settings(
				"ToDo",
				{"fields": [{"fieldname": "not_a_real_field", "label": "Nope"}]},
				[],
			)

	def test_duplicate_role_is_rejected(self):
		frappe.set_user("Administrator")
		settings = frappe.get_single("Logistics Settings")
		settings.append("list_settings_roles", {"role": self.role})
		with self.assertRaises(frappe.ValidationError):
			settings.save(ignore_permissions=True)

	def _user(self, role: str) -> str:
		email = f"list.settings.{frappe.generate_hash(length=8)}@example.com"
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "List",
				"user_type": "System User",
				"send_welcome_email": 0,
				"roles": [{"role": role}],
			}
		).insert(ignore_permissions=True)
		return user.name

	def _restore_todo_list(self):
		current = {
			row.name: row.value
			for row in frappe.get_all(
				"Property Setter",
				filters={"doc_type": "ToDo", "property": "in_list_view"},
				fields=["name", "value"],
			)
		}
		for name in set(current) - set(self._setters):
			frappe.delete_doc("Property Setter", name, ignore_permissions=True, force=True)
		for name, value in self._setters.items():
			if current.get(name) != value and frappe.db.exists("Property Setter", name):
				setter = frappe.get_doc("Property Setter", name)
				setter.flags.ignore_permissions = True
				setter.value = value
				setter.save(ignore_permissions=True)
		if self._list_existed:
			doc = frappe.get_doc("List View Settings", "ToDo")
			doc.flags.ignore_permissions = True
			doc.disable_count = self._previous_count or 0
			doc.fields = self._previous_fields
			doc.save(ignore_permissions=True)
		elif frappe.db.exists("List View Settings", "ToDo"):
			frappe.delete_doc("List View Settings", "ToDo", ignore_permissions=True, force=True)
