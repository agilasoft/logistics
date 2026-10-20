# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

import json
import unittest
from pathlib import Path

from logistics.logistics.page.bulk_update_studio.condition import (
	ALLOWED_OPERATORS,
	DEFAULT_LIMIT,
	MAX_LIMIT,
	NO_VALUE_TYPES,
	build_condition_from_rows,
	coerce_limit,
	normalize_update_value,
	split_condition_args,
	validate_condition_json,
)


class TestBulkUpdateCondition(unittest.TestCase):
	def test_empty_rows_preserve_unfiltered_behavior(self):
		self.assertEqual(build_condition_from_rows(None), "")
		self.assertEqual(build_condition_from_rows([]), "")
		self.assertEqual(build_condition_from_rows([{"field": "", "operator": "=", "value": ""}]), "")
		self.assertEqual(validate_condition_json("  "), "")
		self.assertEqual(validate_condition_json(None), "")

	def test_visual_rows_become_an_and_filter_list(self):
		text = build_condition_from_rows(
			[
				{"field": "status", "operator": "=", "value": "Open"},
				{"field": "priority", "operator": "!=", "value": "Low"},
			]
		)
		self.assertEqual(
			json.loads(text),
			[["status", "=", "Open"], ["priority", "!=", "Low"]],
		)

	def test_in_between_and_is_operators(self):
		self.assertEqual(
			json.loads(
				build_condition_from_rows(
					[{"field": "name", "operator": "in", "value": "A, B, C"}]
				)
			),
			[["name", "in", ["A", "B", "C"]]],
		)
		self.assertEqual(
			json.loads(
				build_condition_from_rows(
					[{"field": "priority", "operator": "between", "value": "Low", "value_to": "High"}]
				)
			),
			[["priority", "between", ["Low", "High"]]],
		)
		self.assertEqual(
			json.loads(
				build_condition_from_rows([{"field": "description", "operator": "is", "value": "set"}])
			),
			[["description", "is", "set"]],
		)

	def test_rejects_unknown_operator_and_incomplete_rows(self):
		with self.assertRaises(ValueError):
			build_condition_from_rows([{"field": "status", "operator": "regex", "value": "Open"}])
		with self.assertRaises(ValueError):
			build_condition_from_rows([{"field": "status", "operator": "=", "value": ""}])
		with self.assertRaises(ValueError):
			build_condition_from_rows([{"field": "status = 1", "operator": "=", "value": "Open"}])
		self.assertNotIn("regex", ALLOWED_OPERATORS)

	def test_advanced_json_passes_through_and_rejects_garbage(self):
		original = '{"status": "Open", "name": ["in", ["TODO-1"]]}'
		self.assertEqual(validate_condition_json(original), original)
		or_filters = '{"priority": "High", "or_filters": [["status", "=", "Open"]]}'
		self.assertEqual(validate_condition_json(or_filters), or_filters)
		self.assertEqual(
			split_condition_args(or_filters),
			{"filters": {"priority": "High"}, "or_filters": [["status", "=", "Open"]]},
		)
		with self.assertRaises(ValueError):
			validate_condition_json("{not json}")
		with self.assertRaises(ValueError):
			validate_condition_json("12")

	def test_limit_matches_frappe_rule(self):
		self.assertEqual(coerce_limit(None), MAX_LIMIT)
		self.assertEqual(coerce_limit(""), DEFAULT_LIMIT)
		self.assertEqual(coerce_limit(0), 500)
		self.assertEqual(coerce_limit(10), 10)
		self.assertEqual(coerce_limit(500), 500)
		self.assertEqual(coerce_limit(501), 500)
		self.assertEqual(coerce_limit("10.8"), 10)
		self.assertEqual(MAX_LIMIT, 500)

	def test_check_and_blank_values(self):
		self.assertEqual(normalize_update_value(0, "Check"), "0")
		self.assertEqual(normalize_update_value("yes", "Check"), "1")
		self.assertEqual(normalize_update_value("  2000 ", "Int"), "2000")
		self.assertEqual(normalize_update_value("", "Data"), "")
		self.assertEqual(normalize_update_value("  keep  ", "Small Text"), "  keep  ")

	def test_layout_fields_are_not_updatable(self):
		for fieldtype in ("Section Break", "Table", "Button", "HTML", "Heading"):
			self.assertIn(fieldtype, NO_VALUE_TYPES)

	def test_page_delegates_to_core_bulk_update(self):
		source = Path(__file__).with_name("bulk_update_studio.py").read_text(encoding="utf-8")
		self.assertIn("doc.bulk_update()", source)
		self.assertNotIn("set_value", source)
		self.assertNotIn("frappe.db.sql", source)

	def test_desk_registration_matches_permission_studio(self):
		root = Path(__file__).resolve().parents[3]
		page = json.loads((Path(__file__).with_name("bulk_update_studio.json")).read_text(encoding="utf-8"))
		self.assertEqual(page["name"], "bulk-update-studio")
		self.assertEqual(page["roles"][0]["role"], "System Manager")
		hooks = (root / "hooks.py").read_text(encoding="utf-8")
		self.assertIn('"bulk-update-studio"', hooks)
		self.assertIn("bulk_update_studio.css", hooks)
		workspace = json.loads(
			(root / "logistics" / "workspace" / "utilities" / "utilities.json").read_text(encoding="utf-8")
		)
		self.assertTrue(any(row.get("link_to") == "bulk-update-studio" for row in workspace["shortcuts"]))
		self.assertTrue(any(row.get("link_to") == "bulk-update-studio" for row in workspace["links"]))
		sidebar = json.loads(
			(root / "logistics" / "sidebar" / "logistics" / "logistics.json").read_text(encoding="utf-8")
		)
		self.assertTrue(any(row.get("link_to") == "bulk-update-studio" for row in sidebar["items"]))

	def test_permission_studio_is_removed_without_deleting_user_permissions(self):
		root = Path(__file__).resolve().parents[3]
		sidebar = json.loads(
			(root / "logistics" / "sidebar" / "logistics" / "logistics.json").read_text(encoding="utf-8")
		)
		workspace = json.loads(
			(root / "logistics" / "workspace" / "utilities" / "utilities.json").read_text(encoding="utf-8")
		)
		self.assertFalse(any(row.get("link_to") == "permission-studio" for row in sidebar["items"]))
		self.assertFalse(any(row.get("link_to") == "permission-studio" for row in workspace["shortcuts"]))
		self.assertFalse(any(row.get("link_to") == "permission-studio" for row in workspace["links"]))
		self.assertNotIn("permission-studio", workspace["content"])
		self.assertFalse((root / "logistics" / "page" / "permission_studio").exists())
		self.assertFalse((root / "permissions").exists())
		patches = (root / "patches.txt").read_text(encoding="utf-8")
		self.assertIn("logistics.patches.v3_0_remove_permission_studio", patches)
		self.assertNotIn("v3_0_sync_permission_studio", patches)
		self.assertIn("logistics.patches.v3_0_sync_utilities_bulk_update_studio", patches)
		source = (root / "patches" / "v3_0_remove_permission_studio.py").read_text(encoding="utf-8")
		self.assertIn("ps_group", source)
		self.assertIn("ps_signature", source)
		self.assertNotIn('delete_doc("User Permission"', source)
		self.assertNotIn("DROP TABLE `tabUser Permission`", source)
		self.assertNotIn("DROP TABLE IF EXISTS `tabUser Permission`", source)
