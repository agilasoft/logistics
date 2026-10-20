# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Integration coverage for the Bulk Update Studio wrapper.

Record changes go through BulkUpdate.bulk_update(), which commits each
document. Cleanup is explicit.
"""

import frappe
from frappe.desk.doctype.bulk_update.bulk_update import BulkUpdate
from frappe.tests import IntegrationTestCase

from logistics.logistics.page.bulk_update_studio.bulk_update_studio import (
	execute_bulk_update,
	get_eligible_fields,
	preview_matching_records,
)


class TestBulkUpdateStudio(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.todo_names = []

	def tearDown(self):
		frappe.set_user("Administrator")
		for name in self.todo_names:
			if frappe.db.exists("ToDo", name):
				frappe.delete_doc("ToDo", name, force=True, ignore_permissions=True)
		frappe.db.commit()

	def _todo(self, description, status="Open", priority="Low"):
		doc = frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": description,
				"status": status,
				"priority": priority,
			}
		).insert(ignore_permissions=True)
		self.todo_names.append(doc.name)
		return doc.name

	def test_eligible_fields_follow_the_standard_form(self):
		data = get_eligible_fields("ToDo")
		fieldnames = [row["fieldname"] for row in data["update_fields"]]
		labels = {row["fieldname"]: row["label"] for row in data["update_fields"]}
		self.assertIn("description", fieldnames)
		self.assertIn("status", fieldnames)
		self.assertIn("priority", fieldnames)
		self.assertNotIn("name", fieldnames)
		self.assertEqual(labels["description"], "Description")
		self.assertTrue(any(row["fieldname"] == "name" for row in data["condition_fields"]))

	def test_execute_updates_through_core_and_respects_conditions(self):
		match = self._todo("Bulk Update Studio match", priority="Low")
		other = self._todo("Bulk Update Studio other", priority="Low")
		before_single = frappe.db.get_single_value("Bulk Update", "document_type")

		result = execute_bulk_update(
			document_type="ToDo",
			field="priority",
			update_value="High",
			conditions=[{"field": "name", "operator": "=", "value": match}],
			limit=10,
		)

		self.assertEqual(result["failed"], [])
		self.assertFalse(result["enqueued"])
		self.assertEqual(frappe.db.get_value("ToDo", match, "priority"), "High")
		self.assertEqual(frappe.db.get_value("ToDo", other, "priority"), "Low")
		frappe.clear_document_cache("Bulk Update")
		self.assertEqual(frappe.db.get_single_value("Bulk Update", "document_type"), before_single)

	def test_preview_is_read_only(self):
		name = self._todo("Bulk Update Studio preview", priority="Medium")
		result = preview_matching_records(
			document_type="ToDo",
			field="priority",
			update_value="High",
			conditions=[{"field": "name", "operator": "=", "value": name}],
			limit=5,
		)
		self.assertEqual(result["shown"], 1)
		self.assertEqual(result["records"][0]["name"], name)
		self.assertEqual(result["records"][0]["current_value"], "Medium")
		self.assertEqual(result["update_value"], "High")
		self.assertEqual(frappe.db.get_value("ToDo", name, "priority"), "Medium")

	def test_invalid_value_is_reported_by_core_without_a_fabricated_count(self):
		name = self._todo("Bulk Update Studio invalid date")
		result = execute_bulk_update(
			document_type="ToDo",
			field="date",
			update_value="not-a-date",
			conditions=[{"field": "name", "operator": "=", "value": name}],
			limit=5,
		)
		self.assertEqual(result["failed"], [name])
		self.assertIsNone(result.get("updated"))
		self.assertFalse(frappe.db.get_value("ToDo", name, "date"))

	def test_wrapper_passes_empty_condition_and_capped_limit_to_core(self):
		captured = {}
		original = BulkUpdate.bulk_update

		def fake(self):
			captured["document_type"] = self.document_type
			captured["field"] = self.field
			captured["update_value"] = self.update_value
			captured["condition"] = self.condition
			captured["limit"] = self.limit
			return []

		BulkUpdate.bulk_update = fake
		try:
			execute_bulk_update(
				document_type="ToDo",
				field="priority",
				update_value="High",
				condition="",
				conditions=[{"field": "", "operator": "=", "value": ""}],
				limit=900,
			)
		finally:
			BulkUpdate.bulk_update = original

		self.assertEqual(captured["document_type"], "ToDo")
		self.assertEqual(captured["field"], "priority")
		self.assertEqual(captured["update_value"], "High")
		self.assertEqual(captured["condition"], "")
		self.assertEqual(captured["limit"], 500)

	def test_invalid_condition_and_unknown_field_are_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			execute_bulk_update(
				document_type="ToDo",
				field="priority",
				update_value="High",
				condition="{not json}",
				limit=5,
			)
		with self.assertRaises(frappe.ValidationError):
			execute_bulk_update(
				document_type="ToDo",
				field="not_a_real_field",
				update_value="High",
				limit=5,
			)
		with self.assertRaises(frappe.ValidationError):
			get_eligible_fields("DocType")
		with self.assertRaises(frappe.ValidationError):
			execute_bulk_update(
				document_type="ToDo",
				field="priority",
				update_value="",
				limit=5,
			)

	def test_system_manager_is_required(self):
		email = "bulk-update-studio-no-role@example.com"
		role = "_Test Bulk Update Studio Role"
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
				ignore_permissions=True
			)
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "Bulk Update",
					"send_welcome_email": 0,
					"roles": [{"role": role}],
				}
			).insert(ignore_permissions=True)
		frappe.db.commit()
		frappe.set_user(email)
		try:
			with self.assertRaises(frappe.PermissionError):
				get_eligible_fields("ToDo")
		finally:
			frappe.set_user("Administrator")
