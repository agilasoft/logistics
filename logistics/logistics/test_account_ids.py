# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import ast
import unittest
from pathlib import Path

from logistics.logistics.account_ids import (
	apply_account_id_updates,
	expected_account_id,
	plan_account_id_updates,
)

PACKAGE = Path(__file__).resolve().parents[1]


class TestExpectedAccountId(unittest.TestCase):
	def test_number_name_and_abbreviation(self):
		self.assertEqual(expected_account_id("100", "Cash", "AB"), "100 - Cash - AB")

	def test_name_and_abbreviation_when_number_is_blank(self):
		self.assertEqual(expected_account_id("  ", "Cash", "AB"), "Cash - AB")
		self.assertEqual(expected_account_id(None, "Cash", "AB"), "Cash - AB")

	def test_strips_name_and_number_only(self):
		self.assertEqual(expected_account_id(" 100 ", "  Cash  ", "AB"), "100 - Cash - AB")

	def test_keeps_abbreviation_already_present_in_the_name(self):
		self.assertEqual(expected_account_id(None, "Cash - AB", "AB"), "Cash - AB - AB")

	def test_missing_name_or_abbreviation(self):
		self.assertIsNone(expected_account_id("100", "  ", "AB"))
		self.assertIsNone(expected_account_id("100", "Cash", ""))
		self.assertIsNone(expected_account_id("100", "Cash", None))


class TestPlanAccountIdUpdates(unittest.TestCase):
	def test_plans_only_ids_that_differ(self):
		plan = plan_account_id_updates(
			[
				{"name": "Cash - AB", "account_name": "Petty Cash", "account_number": None, "company_abbr": "AB"},
				{"name": "100 - Sales - AB", "account_name": "Sales", "account_number": "100", "company_abbr": "AB"},
			]
		)
		self.assertEqual(plan["updates"], [{"from": "Cash - AB", "to": "Petty Cash - AB"}])
		self.assertEqual(plan["collisions"], [])

	def test_case_only_change_is_an_update(self):
		plan = plan_account_id_updates(
			[{"name": "cash - AB", "account_name": "Cash", "account_number": None, "company_abbr": "AB"}]
		)
		self.assertEqual(plan["updates"], [{"from": "cash - AB", "to": "Cash - AB"}])

	def test_swap_and_chain_are_not_collisions(self):
		swap = plan_account_id_updates(
			[
				{"name": "Cash - AB", "account_name": "Bank", "account_number": None, "company_abbr": "AB"},
				{"name": "Bank - AB", "account_name": "Cash", "account_number": None, "company_abbr": "AB"},
			]
		)
		self.assertEqual(len(swap["updates"]), 2)
		self.assertEqual(swap["collisions"], [])

		chain = plan_account_id_updates(
			[
				{"name": "Cash - AB", "account_name": "Bank", "account_number": None, "company_abbr": "AB"},
				{"name": "Bank - AB", "account_name": "Petty", "account_number": None, "company_abbr": "AB"},
			]
		)
		self.assertEqual(chain["collisions"], [])

	def test_collision_with_an_account_that_stays(self):
		plan = plan_account_id_updates(
			[
				{"name": "Cash - AB", "account_name": "Bank", "account_number": None, "company_abbr": "AB"},
				{"name": "Bank - AB", "account_name": "Bank", "account_number": None, "company_abbr": "AB"},
			]
		)
		self.assertEqual(plan["updates"], [])
		self.assertEqual(
			plan["collisions"],
			[{"from": "Cash - AB", "to": "Bank - AB", "existing": "Bank - AB", "reason": "occupied"}],
		)

	def test_case_insensitive_collision(self):
		plan = plan_account_id_updates(
			[
				{"name": "Petty - AB", "account_name": "cash", "account_number": None, "company_abbr": "AB"},
				{"name": "Cash - AB", "account_name": "Cash", "account_number": None, "company_abbr": "AB"},
			]
		)
		self.assertEqual(plan["collisions"][0]["existing"], "Cash - AB")
		self.assertEqual(plan["collisions"][0]["reason"], "occupied")

	def test_duplicate_targets(self):
		plan = plan_account_id_updates(
			[
				{"name": "Old A - AB", "account_name": "Cash", "account_number": None, "company_abbr": "AB"},
				{"name": "Old B - AB", "account_name": "Cash", "account_number": None, "company_abbr": "AB"},
			]
		)
		self.assertEqual(plan["updates"], [])
		self.assertEqual(len(plan["collisions"]), 1)
		self.assertEqual(plan["collisions"][0]["reason"], "duplicate")
		self.assertEqual(plan["collisions"][0]["to"], "Cash - AB")

	def test_skips_missing_and_overlong_ids(self):
		plan = plan_account_id_updates(
			[
				{"name": "Blank - AB", "account_name": " ", "account_number": None, "company_abbr": "AB"},
				{"name": "No Co", "account_name": "Cash", "account_number": None, "company_abbr": None},
				{
					"name": "Long - AB",
					"account_name": "L" * 140,
					"account_number": None,
					"company_abbr": "AB",
				},
			],
			name_length=140,
		)
		self.assertEqual(plan["updates"], [])
		reasons = {row["name"]: row["reason"] for row in plan["skipped"]}
		self.assertEqual(reasons["Blank - AB"], "missing")
		self.assertEqual(reasons["No Co"], "missing")
		self.assertEqual(reasons["Long - AB"], "too_long")


class TestApplyAccountIdUpdates(unittest.TestCase):
	def test_swap_renames_through_temporary_ids(self):
		state = {"Cash - AB": "cash-row", "Bank - AB": "bank-row"}
		calls = []

		def rename(old, new):
			self.assertIn(old, state)
			self.assertNotIn(new, state)
			calls.append((old, new))
			state[new] = state.pop(old)

		renamed = apply_account_id_updates(
			[{"from": "Cash - AB", "to": "Bank - AB"}, {"from": "Bank - AB", "to": "Cash - AB"}],
			rename,
			list(state),
		)
		self.assertEqual(state["Bank - AB"], "cash-row")
		self.assertEqual(state["Cash - AB"], "bank-row")
		self.assertTrue(all(new.startswith("__ren__") for _old, new in calls[:2]))
		self.assertEqual([new for _old, new in calls[2:]], ["Bank - AB", "Cash - AB"])
		self.assertEqual(renamed[0]["from"], "Cash - AB")
		self.assertEqual(renamed[0]["to"], "Bank - AB")

	def test_empty_plan_does_not_rename(self):
		def rename(old, new):
			raise AssertionError((old, new))

		self.assertEqual(apply_account_id_updates([], rename, []), [])


class TestAccountIdActionWiring(unittest.TestCase):
	def test_list_and_tree_load_the_action(self):
		hooks = ast.parse((PACKAGE / "hooks.py").read_text())
		found = {}
		for node in hooks.body:
			if not isinstance(node, ast.Assign):
				continue
			for target in node.targets:
				if isinstance(target, ast.Name) and target.id in {"doctype_list_js", "doctype_tree_js"}:
					found[target.id] = ast.literal_eval(node.value)
		self.assertEqual(found["doctype_list_js"]["Account"], "public/js/account_ids.js")
		self.assertEqual(found["doctype_tree_js"]["Account"], "public/js/account_ids.js")

		script = (PACKAGE / "public" / "js" / "account_ids.js").read_text()
		self.assertIn('__("Update Account IDs")', script)
		self.assertIn("logistics.logistics.account_ids.update_account_ids", script)
		self.assertIn('frappe.listview_settings["Account"]', script)
		self.assertIn('frappe.treeview_settings["Account"]', script)
		self.assertIn("menu_items", script)


if __name__ == "__main__":
	unittest.main()
