# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Cost Center form customization no longer shows Company."""

import json
import unittest
from pathlib import Path


def _customization():
	path = Path(__file__).resolve().parents[1] / "custom" / "cost_center.json"
	return json.loads(path.read_text())


class TestCostCenterCompanyField(unittest.TestCase):
	def test_company_is_hidden_and_absent_from_layout(self):
		data = _customization()
		setters = {(row.get("field_name"), row.get("property")): row.get("value") for row in data["property_setters"]}

		self.assertEqual(setters[("company", "hidden")], "1")
		self.assertEqual(setters[("company", "in_list_view")], "0")
		self.assertEqual(setters[("company", "in_standard_filter")], "0")
		self.assertEqual(setters[("company", "reqd")], "0")

		order = json.loads(setters[(None, "field_order")])
		self.assertNotIn("company", order)
		self.assertIn("custom_branch", order)

		search_fields = setters[(None, "search_fields")]
		self.assertNotIn("company", search_fields.split(","))

		branch = next(row for row in data["custom_fields"] if row["fieldname"] == "custom_branch")
		self.assertEqual(branch["insert_after"], "parent_cost_center")

	def test_tree_dialog_does_not_ask_for_company(self):
		root = Path(__file__).resolve().parents[2]
		hooks = (root / "hooks.py").read_text()
		self.assertIn('"Cost Center": "public/js/cost_center_tree.js"', hooks)

		tree_js = (root / "public" / "js" / "cost_center_tree.js").read_text()
		self.assertIn('frappe.treeview_settings["Cost Center"]', tree_js)
		self.assertIn("ignore_fields", tree_js)
		self.assertIn('"company"', tree_js)

		patch = (root / "patches" / "v3_0_hide_cost_center_company.py").read_text()
		self.assertIn('("reqd", "Check", "0")', patch)
