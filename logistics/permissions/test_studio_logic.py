# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

import unittest
from pathlib import Path

from logistics.permissions.studio_logic import (
	PICKER_PAGE_SIZE,
	access_summary,
	analyze_health,
	assemble_picker,
	build_matrix,
	bulk_member_plan,
	copy_values,
	dashboard_cards,
	desired_permissions,
	explain_access,
	filter_activity,
	filter_groups,
	group_from_template,
	plan_sync,
	removal_is_managed,
	stored_status,
	toggle_selected,
	user_permission_blocks,
)


class TestSyncPlan(unittest.TestCase):
	def test_manual_permissions_are_not_removed_or_claimed(self):
		desired = desired_permissions(
			1,
			["ada@example.com"],
			[{"allow": "Company", "for_value": "Alta", "applicable_for": ""}],
		)
		manual = [{"name": "UP-MANUAL", "user": "ada@example.com", "allow": "Company", "for_value": "Alta", "ps_group": ""}]
		plan = plan_sync(desired, managed=[], manual=manual)
		self.assertEqual(plan["create"], [])
		self.assertEqual(plan["remove"], [])
		self.assertEqual(len(plan["kept_manual"]), 1)
		self.assertFalse(removal_is_managed(manual[0], "AFE"))

	def test_duplicate_owned_rows_are_collapsed(self):
		desired = desired_permissions(
			1,
			["ada@example.com"],
			[{"allow": "Company", "for_value": "Alta"}],
		)
		managed = [
			{"name": "UP-1", "user": "ada@example.com", "allow": "Company", "for_value": "Alta", "ps_group": "AFE", "signature": desired[0]["signature"], "is_default": 0, "hide_descendants": 0, "applicable_for": ""},
			{"name": "UP-2", "user": "ada@example.com", "allow": "Company", "for_value": "Alta", "ps_group": "AFE", "signature": desired[0]["signature"], "is_default": 0, "hide_descendants": 0, "applicable_for": ""},
		]
		plan = plan_sync(desired, managed, manual=[])
		self.assertEqual([row["name"] for row in plan["remove"]], ["UP-2"])
		self.assertEqual(plan["create"], [])

	def test_only_owned_rows_are_removed(self):
		managed = [
			{
				"name": "UP-OWNED",
				"user": "ada@example.com",
				"allow": "Company",
				"for_value": "Old",
				"ps_group": "AFE",
				"signature": "old",
			}
		]
		plan = plan_sync([], managed, manual=[{"name": "UP-MANUAL", "user": "ada@example.com", "allow": "Branch", "for_value": "MNL", "ps_group": ""}])
		self.assertEqual([row["name"] for row in plan["remove"]], ["UP-OWNED"])
		self.assertTrue(removal_is_managed(plan["remove"][0], "AFE"))
		self.assertFalse(removal_is_managed({"name": "UP-MANUAL", "ps_group": ""}, "AFE"))

	def test_disabled_group_has_nothing_to_keep(self):
		rows = desired_permissions(
			0,
			["ada@example.com"],
			[{"allow": "Company", "for_value": "Alta"}],
		)
		self.assertEqual(rows, [])

	def test_pending_and_failed_status(self):
		self.assertEqual(stored_status("Syncing", "a", "b", ""), "Syncing")
		self.assertEqual(stored_status("", "abc", "abc", ""), "In Sync")
		self.assertEqual(stored_status("", "abc", "def", ""), "Changes Pending")
		self.assertEqual(stored_status("Sync Failed", "abc", "def", "boom"), "Sync Failed")


class TestPicker(unittest.TestCase):
	def test_clearing_search_keeps_the_checked_document(self):
		documents = [{"name": f"Doc {index}", "label": f"Doc {index}"} for index in range(40)]
		searched = assemble_picker(documents, selected=[], tagged=[], query="Doc 30")
		match = next(row for row in searched["rows"] if row["name"] == "Doc 30")
		self.assertTrue(match["checked"] is False)
		selected = toggle_selected([], match, True)
		cleared = assemble_picker(documents, selected=selected, tagged=[], query="")
		kept = next(row for row in cleared["rows"] if row["name"] == "Doc 30")
		self.assertTrue(kept["checked"])
		self.assertIn("Doc 30", cleared["selected"])
		self.assertEqual(cleared["viewport_rows"], PICKER_PAGE_SIZE)

	def test_tagged_documents_from_another_doctype_stay_visible(self):
		tagged = [
			{
				"name": "ALTA FAIRS",
				"label": "ALTA FAIRS",
				"tags": [{"group": "AFE", "applicable_for": "Sales Quote", "source": "Permission Group"}],
			}
		]
		view = assemble_picker(
			[{"name": "Other Co", "label": "Other Co"}],
			selected=[],
			tagged=tagged,
			query="",
		)
		row = next(item for item in view["rows"] if item["name"] == "ALTA FAIRS")
		self.assertEqual(row["source"], "tagged")
		self.assertFalse(row["checked"])
		self.assertEqual(row["tags"][0]["applicable_for"], "Sales Quote")

	def test_selected_rows_are_not_limited_to_the_visible_page(self):
		selected = [{"name": f"Sel {index}", "label": f"Sel {index}"} for index in range(30)]
		view = assemble_picker([{"name": "Extra", "label": "Extra"}], selected=selected, tagged=[], query="")
		checked = [row for row in view["rows"] if row["checked"]]
		self.assertEqual(len(checked), 30)
		self.assertEqual(view["viewport_rows"], 25)
		self.assertGreater(view["total"], 25)


class TestHealthAndAccess(unittest.TestCase):
	def test_health_rules_and_severity(self):
		report = analyze_health(
			groups=[
				{
					"name": "AFE",
					"sync_status": "Sync Failed",
					"members": [],
					"permitted_values": [{"allow": "Company", "for_value": "Missing"}],
				},
				{
					"name": "SAL",
					"sync_status": "Changes Pending",
					"members": ["ada@example.com"],
					"permitted_values": [{"allow": "Company", "for_value": "Alta"}],
				},
			],
			managed=[
				{"name": "UP-1", "user": "ada@example.com", "allow": "Company", "for_value": "Alta", "ps_group": "GONE"}
			],
			manual=[
				{"name": "UP-2", "user": "ada@example.com", "allow": "Company", "for_value": "Alta", "ps_group": ""}
			],
			enabled_users=["ada@example.com", "no-group@example.com", "Guest"],
			invalid_values=[{"group": "AFE", "allow": "Company", "for_value": "Missing"}],
			orphan_groups=["GONE"],
		)
		codes = [issue["code"] for issue in report["issues"]]
		self.assertIn("invalid_values", codes)
		self.assertIn("sync_failed", codes)
		self.assertIn("empty_groups", codes)
		self.assertIn("unsynchronized", codes)
		self.assertIn("duplicate_permissions", codes)
		self.assertIn("orphaned", codes)
		self.assertIn("users_without_groups", codes)
		users_issue = next(issue for issue in report["issues"] if issue["code"] == "users_without_groups")
		self.assertNotIn("Guest", users_issue["records"])
		self.assertEqual(report["issues"][0]["severity"], "Critical")

	def test_access_explanation_does_not_invent_a_reason(self):
		unknown = explain_access(
			{
				"allowed": False,
				"user": "ada@example.com",
				"doctype": "Sales Invoice",
				"action": "read",
				"user_enabled": True,
				"role_has_right": True,
				"blocking_user_permissions": [],
				"user_permissions_evaluated": True,
			}
		)
		self.assertEqual(unknown["status"], "Access Denied")
		self.assertEqual(unknown["reliable_reasons"], [])
		self.assertIn("did not identify", unknown["summary"])

		blocked = explain_access(
			{
				"allowed": False,
				"user": "ada@example.com",
				"doctype": "Sales Invoice",
				"action": "read",
				"user_enabled": True,
				"role_has_right": True,
				"blocking_user_permissions": user_permission_blocks(
					"Sales Invoice",
					{"company": {"doctype": "Company", "value": "Other"}},
					[{"allow": "Company", "for_value": "Alta", "applicable_for": "", "apply_to_all_doctypes": 1}],
				),
			}
		)
		self.assertTrue(blocked["reliable_reasons"])
		self.assertIn("Alta", blocked["summary"])

	def test_allowed_result_does_not_claim_a_denial(self):
		result = explain_access(
			{
				"allowed": True,
				"user_enabled": True,
				"role_has_right": False,
				"blocking_user_permissions": [
					{"allow": "Company", "field": "company", "document_value": "Other", "permitted": ["Alta"]}
				],
			}
		)
		self.assertEqual(result["status"], "Access Allowed")
		self.assertEqual(result["reliable_reasons"], [])

	def test_user_permission_for_another_doctype_does_not_block(self):
		blocks = user_permission_blocks(
			"Sales Invoice",
			{"company": {"doctype": "Company", "value": "Other"}},
			[{"allow": "Company", "for_value": "Alta", "applicable_for": "Sales Order", "apply_to_all_doctypes": 0}],
		)
		self.assertEqual(blocks, [])


class TestStudioViews(unittest.TestCase):
	def test_matrix_marks_configuration_not_grants(self):
		matrix = build_matrix(
			[
				{"name": "AFE", "permitted_values": [{"allow": "Company", "for_value": "Alta", "applicable_for": ""}]},
				{"name": "SAL", "permitted_values": [{"allow": "Branch", "for_value": "MNL", "applicable_for": "Sales Quote"}]},
			]
		)
		company = next(row for row in matrix["rows"] if row["field"] == "Company")
		self.assertTrue(company["cells"]["AFE"]["configured"])
		self.assertFalse(company["cells"]["SAL"]["configured"])
		self.assertTrue(company["different"])
		self.assertIn("does not grant", matrix["note"])

	def test_template_does_not_copy_members_unless_asked(self):
		group = group_from_template(
			{
				"description": "Accounting",
				"category": "Accounting",
				"members": ["ada@example.com"],
				"permitted_values": [{"allow": "Company", "for_value": "Alta", "applicable_for": "Sales Invoice"}],
			},
			"New Group",
		)
		self.assertEqual(group["members"], [])
		self.assertEqual(group["permitted_values"][0]["for_value"], "Alta")

	def test_copy_skips_existing_values(self):
		plan = copy_values(
			[{"allow": "Company", "for_value": "Alta"}, {"allow": "Branch", "for_value": "MNL"}],
			[{"allow": "Company", "for_value": "Alta", "applicable_for": ""}],
		)
		self.assertEqual(len(plan["add"]), 1)
		self.assertEqual(plan["add"][0]["for_value"], "MNL")

	def test_dashboard_hides_trend_without_history(self):
		cards = dashboard_cards({"groups": 4, "issues": 1}, {"groups": 2}, False)
		self.assertNotIn("delta", cards[0])
		cards = dashboard_cards(
			{"groups": 4, "users_in_groups": 1, "users_without_groups": 1, "managed_permissions": 1, "issues": 1},
			{"groups": 2, "issues": 3},
			True,
		)
		self.assertEqual(cards[0]["delta"], 2)
		self.assertEqual(cards[-1]["target"], "health")

	def test_filters(self):
		groups = [
			{"name": "AFE", "group_name": "Alta Fairs", "description": "Exhibits", "sync_status": "In Sync", "category": "Sales", "enabled": 1, "member_count": 2, "modified": "2026-10-02 00:00:00"},
			{"name": "ACC", "group_name": "Accounting", "description": "Ledger", "sync_status": "Sync Failed", "category": "Accounting", "enabled": 0, "member_count": 5, "modified": "2026-10-01 00:00:00"},
		]
		found = filter_groups(groups, search="exhibit", status="In Sync")
		self.assertEqual(found["total"], 1)
		ordered = filter_groups(groups, sort="members")
		self.assertEqual(ordered["rows"][0]["name"], "ACC")
		activity = filter_activity(
			[{"action": "Sync Failed", "owner": "Ada", "creation": "2026-10-02 10:00:00", "details": "Company"}],
			query="company",
			action="Sync Failed",
			date_from="2026-10-01",
		)
		self.assertEqual(len(activity), 1)

	def test_summary_does_not_describe_a_grant(self):
		summary = access_summary(
			["ada@example.com"],
			[{"allow": "Company", "for_value": "Alta", "applicable_for": "Sales Quote"}],
		)
		self.assertIn("do not grant", summary["note"])
		self.assertEqual(summary["applicable_doctypes"], ["Sales Quote"])

	def test_member_plan(self):
		plan = bulk_member_plan(["ada@example.com"], ["ada@example.com", "bo@example.com"], "add_members")
		self.assertEqual(plan["add"], ["bo@example.com"])

	def test_picker_script_keeps_selection_outside_the_search_box(self):
		source = Path(__file__).resolve().parents[1].joinpath("public/js/permission_studio_picker.js").read_text()
		page = Path(__file__).resolve().parents[1].joinpath("public/js/permission_studio_page.js").read_text()
		self.assertIn("source !== \"selected\"", source)
		self.assertIn("state.selected = picker.toggleSelected", page)
		self.assertIn("viewportRows", source)
		self.assertIn("max-height:min", page)
