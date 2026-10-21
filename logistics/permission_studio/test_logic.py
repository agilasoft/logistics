# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

import unittest
from pathlib import Path

from logistics.permission_studio.flags import as_flag
from logistics.permission_studio.logic import (
	blocked_defaults,
	collect_grants,
	coverage_rows,
	default_conflicts,
	diff_permissions,
	group_matches,
	matrix_for,
	requested_group_name,
	validate_group_shape,
)


def _group(name="North", enabled=1, members=None, rules=None, **extra):
	payload = {
		"name": name,
		"group_name": name,
		"enabled": enabled,
		"members": members if members is not None else [{"user": "a@example.com", "full_name": "Ada"}],
		"rules": rules
		if rules is not None
		else [
			{
				"reference_doctype": "Company",
				"for_value": "North Co",
				"apply_to_all_doctypes": 1,
				"is_default": 1,
			}
		],
	}
	payload.update(extra)
	return payload


class TestFlags(unittest.TestCase):
	def test_string_zero_is_false(self):
		self.assertEqual(as_flag("0"), 0)
		self.assertEqual(as_flag("1"), 1)
		self.assertEqual(as_flag(0), 0)
		self.assertEqual(as_flag(True), 1)


class TestGroupShape(unittest.TestCase):
	def test_accepts_a_plain_group(self):
		self.assertEqual(validate_group_shape(_group()), [])

	def test_rejects_guest_and_duplicate_users(self):
		errors = validate_group_shape(
			_group(members=[{"user": "Guest"}, {"user": "a@example.com"}, {"user": "A@example.com"}])
		)
		self.assertTrue(any("Guest" in error for error in errors))
		self.assertTrue(any("more than once" in error for error in errors))

	def test_rejects_duplicate_rules_and_missing_applicable_for(self):
		errors = validate_group_shape(
			_group(
				rules=[
					{"reference_doctype": "Company", "for_value": "North Co", "apply_to_all_doctypes": 0},
					{
						"reference_doctype": "Company",
						"for_value": "North Co",
						"apply_to_all_doctypes": 1,
					},
					{
						"reference_doctype": "Company",
						"for_value": "North Co",
						"apply_to_all_doctypes": 1,
					},
				]
			)
		)
		self.assertTrue(any("Applicable For" in error for error in errors))
		self.assertTrue(any("Duplicate permission" in error for error in errors))

	def test_rejects_bad_color(self):
		self.assertTrue(any("Color" in error for error in validate_group_shape(_group(color="blue"))))


class TestGroupRename(unittest.TestCase):
	def test_keeps_the_name_when_the_request_is_missing_or_unchanged(self):
		self.assertIsNone(requested_group_name("North", None))
		self.assertIsNone(requested_group_name("North", "North"))
		self.assertIsNone(requested_group_name("North", "  North  "))

	def test_returns_a_cleaned_new_name(self):
		self.assertEqual(requested_group_name("North", "  North sales  "), "North sales")

	def test_blank_name_is_rejected(self):
		self.assertEqual(requested_group_name("North", "   "), "")


class TestGrants(unittest.TestCase):
	def test_disabled_group_grants_nothing(self):
		grants, conflicts = collect_grants([_group(enabled=0)])
		self.assertEqual(grants, {})
		self.assertEqual(conflicts, [])

	def test_two_groups_merge_one_grant(self):
		grants, hide_conflicts = collect_grants(
			[
				_group("North"),
				_group("Audit", rules=[{"reference_doctype": "Company", "for_value": "North Co", "apply_to_all_doctypes": 1, "is_default": 0}]),
			]
		)
		self.assertEqual(len(grants), 1)
		grant = next(iter(grants.values()))
		self.assertEqual(grant["groups"], ["Audit", "North"])
		self.assertEqual(grant["is_default"], 1)
		self.assertEqual(hide_conflicts, [])

	def test_hide_descendants_disagreement(self):
		_, hide_conflicts = collect_grants(
			[
				_group(rules=[{"reference_doctype": "Territory", "for_value": "Asia", "apply_to_all_doctypes": 1, "hide_descendants": 1}]),
				_group("Other", rules=[{"reference_doctype": "Territory", "for_value": "Asia", "apply_to_all_doctypes": 1, "hide_descendants": 0}]),
			]
		)
		self.assertEqual(len(hide_conflicts), 1)

	def test_default_conflict_on_overlapping_scope(self):
		grants, _ = collect_grants(
			[
				_group(),
				_group(
					"South",
					rules=[{"reference_doctype": "Company", "for_value": "South Co", "apply_to_all_doctypes": 1, "is_default": 1}],
				),
			]
		)
		conflicts = default_conflicts(grants)
		self.assertEqual(len(conflicts), 1)
		self.assertEqual(conflicts[0]["allow"], "Company")

	def test_no_conflict_when_applicable_for_differs(self):
		grants, _ = collect_grants(
			[
				_group(
					rules=[
						{
							"reference_doctype": "Territory",
							"for_value": "North",
							"apply_to_all_doctypes": 0,
							"applicable_for": "Customer",
							"is_default": 1,
						},
						{
							"reference_doctype": "Territory",
							"for_value": "South",
							"apply_to_all_doctypes": 0,
							"applicable_for": "Sales Invoice",
							"is_default": 1,
						},
					]
				)
			]
		)
		self.assertEqual(default_conflicts(grants), [])

	def test_apply_all_overlaps_a_narrow_default(self):
		grants, _ = collect_grants(
			[
				_group(
					rules=[
						{"reference_doctype": "Company", "for_value": "North Co", "apply_to_all_doctypes": 1, "is_default": 1},
						{
							"reference_doctype": "Company",
							"for_value": "South Co",
							"apply_to_all_doctypes": 0,
							"applicable_for": "Sales Invoice",
							"is_default": 1,
						},
					]
				)
			]
		)
		self.assertEqual(len(default_conflicts(grants)), 1)


class TestDiff(unittest.TestCase):
	def test_creates_updates_deletes_and_keeps_manual(self):
		grants, _ = collect_grants([_group()])
		managed = [
			{
				"name": "UP-OLD",
				"user": "a@example.com",
				"allow": "Company",
				"for_value": "Old Co",
				"apply_to_all_doctypes": 1,
				"applicable_for": None,
				"is_default": 0,
				"hide_descendants": 0,
				"hero_permission_group": "North",
				"hero_source_groups": "North",
			},
			{
				"name": "UP-KEEP",
				"user": "a@example.com",
				"allow": "Company",
				"for_value": "North Co",
				"apply_to_all_doctypes": 1,
				"applicable_for": "",
				"is_default": 0,
				"hide_descendants": 0,
				"hero_permission_group": "Somewhere",
				"hero_source_groups": "Somewhere",
			},
		]
		manual = [
			{
				"name": "UP-MANUAL",
				"user": "b@example.com",
				"allow": "Company",
				"for_value": "North Co",
				"apply_to_all_doctypes": 1,
				"is_default": 1,
				"hide_descendants": 0,
			}
		]
		# Add a second user whose grant is already manual.
		grants, _ = collect_grants(
			[
				_group(
					members=[{"user": "a@example.com"}, {"user": "b@example.com"}],
				)
			]
		)
		diff = diff_permissions(grants, managed, manual)
		self.assertEqual(diff["to_delete"], ["UP-OLD"])
		self.assertEqual([row["name"] for row in diff["to_update"]], ["UP-KEEP"])
		self.assertEqual(diff["to_update"][0]["changes"]["is_default"], 1)
		self.assertEqual(diff["to_update"][0]["changes"]["hero_permission_group"], "North")
		self.assertEqual(len(diff["manual_overlaps"]), 1)
		self.assertEqual(diff["manual_overlaps"][0]["user"], "b@example.com")
		self.assertEqual(diff["to_create"], [])

	def test_manual_default_blocks_a_different_value(self):
		grants, _ = collect_grants([_group()])
		blocked = blocked_defaults(
			grants,
			[
				{
					"name": "UP-MANUAL",
					"user": "a@example.com",
					"allow": "Company",
					"for_value": "Other Co",
					"apply_to_all_doctypes": 1,
					"is_default": 1,
				}
			],
		)
		self.assertEqual(len(blocked), 1)

	def test_same_manual_key_does_not_block(self):
		grants, _ = collect_grants([_group()])
		blocked = blocked_defaults(
			grants,
			[
				{
					"user": "a@example.com",
					"allow": "Company",
					"for_value": "North Co",
					"apply_to_all_doctypes": 1,
					"is_default": 1,
				}
			],
		)
		self.assertEqual(blocked, [])


class TestMatrixAndFilters(unittest.TestCase):
	def test_matrix_puts_values_under_their_doctype(self):
		matrix = matrix_for(
			_group(
				rules=[
					{"reference_doctype": "Company", "for_value": "North Co", "apply_to_all_doctypes": 1, "is_default": 1},
					{"reference_doctype": "Territory", "for_value": "Asia", "apply_to_all_doctypes": 1},
				]
			)
		)
		self.assertEqual(matrix["doctypes"], ["Company", "Territory"])
		self.assertEqual(matrix["rows"][0]["cells"]["Company"][0]["value"], "North Co")
		self.assertEqual(matrix["rows"][0]["cells"]["Company"][0]["is_default"], 1)

	def test_filters(self):
		group = _group(description="Field team")
		group["members"][0]["roles"] = ["Sales User"]
		self.assertTrue(group_matches(group, {"search": "field"}, set()))
		self.assertTrue(group_matches(group, {"role": "Sales User"}, set()))
		self.assertFalse(group_matches(group, {"role": "Accounts Manager"}, set()))
		self.assertTrue(group_matches(group, {"doctype": "Company"}, set()))
		self.assertFalse(group_matches(group, {"doctype": "Warehouse"}, set()))
		self.assertFalse(group_matches(group, {"enabled": "disabled"}, set()))
		self.assertFalse(group_matches(group, {"conflicts_only": 1}, set()))
		self.assertTrue(group_matches(group, {"conflicts_only": 1}, {"North"}))


class TestCoverageRows(unittest.TestCase):
	def test_splits_grouped_and_manual(self):
		users = [
			{"name": "a@example.com", "full_name": "Ada", "enabled": 1, "roles": ["Sales User"]},
			{"name": "b@example.com", "full_name": "Bo", "enabled": 1, "roles": ["Sales User"]},
			{"name": "Guest", "full_name": "Guest", "enabled": 1, "roles": []},
			{"name": "c@example.com", "full_name": "Cy", "enabled": 0, "roles": ["Sales User"]},
		]
		rows = coverage_rows(
			users,
			{"a@example.com": ["North"]},
			{"b@example.com": 2},
			{"enabled_only": 1},
		)
		by_user = {row["user"]: row for row in rows}
		self.assertNotIn("Guest", by_user)
		self.assertNotIn("c@example.com", by_user)
		self.assertEqual(by_user["a@example.com"]["in_group"], "Yes")
		self.assertEqual(by_user["b@example.com"]["manual_permissions"], 2)
		only_manual = coverage_rows(users, {"a@example.com": ["North"]}, {"b@example.com": 2}, {"coverage": "Has manual permissions"})
		self.assertEqual([row["user"] for row in only_manual], ["b@example.com"])


class TestRestoredStudio(unittest.TestCase):
	def test_page_is_the_14_oct_frappe_hero_studio(self):
		root = Path(__file__).resolve().parents[1]
		page = (root / "logistics" / "page" / "permission_studio" / "permission_studio.js").read_text(encoding="utf-8")
		self.assertIn("Permitted values", page)
		self.assertIn("Add values", page)
		self.assertIn('data-action="edit-rule"', page)
		self.assertIn('__("only {0}"', page)
		api = (root / "permission_studio" / "api.py").read_text(encoding="utf-8")
		self.assertIn("def update_rule(", api)
		self.assertIn("logistics.permission_studio.api.add_rules", page)
		self.assertNotIn("frappehero.permission_studio", page)
		self.assertFalse((root / "permissions").exists())
		patch = (root / "patches" / "v3_0_restore_hero_permission_studio.py").read_text(encoding="utf-8")
		self.assertNotIn('delete_doc("User Permission"', patch)
		self.assertNotIn("DROP TABLE `tabUser Permission`", patch)
		self.assertNotIn("Hero Permission Group", patch)
		self.assertIn("ps_group", patch)


if __name__ == "__main__":
	unittest.main()
