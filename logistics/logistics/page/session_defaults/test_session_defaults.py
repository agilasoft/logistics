# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Who must choose a Company, and what Session Defaults will save."""

from __future__ import annotations

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from logistics.logistics.page.session_defaults.session_defaults import (
	get_context,
	get_personal_company,
	get_permitted_companies,
	restore_persistent_company,
	save_session_defaults,
	user_needs_session_defaults,
)


class TestSessionDefaults(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		self._users = []

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.clear_cache()
		super().tearDown()

	def test_system_user_without_company_needs_page(self):
		user = self._system_user()
		company = self._company("Needs")
		self.assertIsNone(get_personal_company(user))
		self.assertIn(company, get_permitted_companies(user))
		self.assertTrue(user_needs_session_defaults(user))

	def test_personal_company_skips_page(self):
		user = self._system_user()
		company = self._company("Personal")
		frappe.set_user(user)
		save_session_defaults(company)
		self.assertEqual(get_personal_company(user), company)
		self.assertFalse(user_needs_session_defaults(user))

	def test_global_default_still_requires_page(self):
		user = self._system_user()
		company = self._company("Global")
		# The site-wide value is stored under the scrubbed key. A title-case
		# "Company" row is the same database key and is invisible to get_user_default.
		frappe.defaults.clear_default("Company", parent="__default")
		frappe.defaults.set_global_default("company", company)
		frappe.set_user(user)
		self.assertEqual(frappe.defaults.get_user_default("Company"), company)
		self.assertIsNone(get_personal_company(user))
		self.assertTrue(user_needs_session_defaults(user))

	def test_website_user_and_guest_skip(self):
		website_user = self._user(user_type="Website User")
		self.assertEqual(frappe.db.get_value("User", website_user, "user_type"), "Website User")
		self.assertFalse(user_needs_session_defaults(website_user))
		self.assertFalse(user_needs_session_defaults("Guest"))

		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			get_context()

	def test_incomplete_setup_skips_page(self):
		user = self._system_user()
		self._company("Wizard")
		with patch("frappe.is_setup_complete", return_value=False):
			self.assertFalse(user_needs_session_defaults(user))

	def test_no_permitted_company_skips(self):
		user = self._system_user()
		with patch(
			"logistics.logistics.page.session_defaults.session_defaults.get_permitted_companies",
			return_value=[],
		):
			self.assertFalse(user_needs_session_defaults(user))

	def test_save_writes_user_default(self):
		user = self._system_user()
		company = self._company("Saved")
		frappe.set_user(user)
		result = save_session_defaults(company)
		self.assertEqual(result["company"], company)
		self.assertEqual(frappe.defaults.get_user_default("Company"), company)
		self.assertEqual(get_personal_company(user), company)
		context = get_context()
		self.assertEqual(context["company"], company)
		self.assertIn(company, context["companies"])
		self.assertFalse(context["required"])

	def test_logout_keeps_personal_company(self):
		user = self._system_user()
		company = self._company("Keep")
		frappe.set_user(user)
		save_session_defaults(company)
		# Session Default Settings clears the company key on logout.
		frappe.defaults.clear_user_default("company", user)
		frappe.defaults.clear_user_default("Company", user)
		self.assertEqual(get_personal_company(user), company)
		self.assertFalse(user_needs_session_defaults(user))
		self.assertEqual(restore_persistent_company(user), company)
		self.assertEqual(frappe.defaults.get_user_default("Company"), company)

	def test_save_writes_branch_cost_center_and_profit_center(self):
		user = self._dimension_user()
		company = self._company("Dims")
		other = self._company("DimsOther")
		branch = self._branch(company)
		cost_center = self._leaf_cost_center(company)
		other_cost_center = self._leaf_cost_center(other)
		profit_center = self._profit_center(company)
		other_profit_center = self._profit_center(other)
		frappe.set_user(user)

		frappe.defaults.set_user_default("company", company, user=user)
		frappe.defaults.set_user_default("logistics_session_company", company, user=user)
		self.assertTrue(user_needs_session_defaults(user))

		with self.assertRaises(frappe.ValidationError):
			save_session_defaults(company, branch=branch, cost_center=cost_center, profit_center="")
		with self.assertRaises(frappe.PermissionError):
			save_session_defaults(
				company,
				branch=branch,
				cost_center=other_cost_center,
				profit_center=profit_center,
			)
		with self.assertRaises(frappe.PermissionError):
			save_session_defaults(
				company,
				branch=branch,
				cost_center=cost_center,
				profit_center=other_profit_center,
			)

		result = save_session_defaults(
			company,
			branch=branch,
			cost_center=cost_center,
			profit_center=profit_center,
		)
		self.assertEqual(result["branch"], branch)
		self.assertEqual(result["cost_center"], cost_center)
		self.assertEqual(result["profit_center"], profit_center)
		self.assertEqual(frappe.defaults.get_user_default("branch"), branch)
		self.assertEqual(frappe.defaults.get_user_default("Branch"), branch)
		self.assertEqual(frappe.defaults.get_user_default("cost_center"), cost_center)
		self.assertEqual(frappe.defaults.get_user_default("Cost Center"), cost_center)
		self.assertEqual(frappe.defaults.get_user_default("profit_center"), profit_center)
		self.assertEqual(frappe.defaults.get_user_default("Profit Center"), profit_center)
		self.assertFalse(user_needs_session_defaults(user))

		context = get_context()
		self.assertEqual(context["branch"], branch)
		self.assertEqual(context["cost_center"], cost_center)
		self.assertEqual(context["profit_center"], profit_center)
		self.assertIn(branch, [row["name"] for row in context["branches"]])
		self.assertIn(cost_center, [row["name"] for row in context["cost_centers"]])
		self.assertIn(profit_center, [row["name"] for row in context["profit_centers"]])

	def test_logout_keeps_dimension_defaults(self):
		user = self._dimension_user()
		company = self._company("KeepDims")
		branch = self._branch(company)
		cost_center = self._leaf_cost_center(company)
		profit_center = self._profit_center(company)
		frappe.set_user(user)
		save_session_defaults(
			company,
			branch=branch,
			cost_center=cost_center,
			profit_center=profit_center,
		)
		for key in ("branch", "Branch", "cost_center", "Cost Center", "profit_center", "Profit Center"):
			frappe.defaults.clear_user_default(key, user)
		self.assertFalse(user_needs_session_defaults(user))
		restored = restore_persistent_company(user)
		self.assertEqual(restored, company)
		self.assertEqual(frappe.defaults.get_user_default("branch"), branch)
		self.assertEqual(frappe.defaults.get_user_default("cost_center"), cost_center)
		self.assertEqual(frappe.defaults.get_user_default("profit_center"), profit_center)

	def test_save_rejects_empty_and_unpermitted_company(self):
		user = self._system_user()
		allowed = self._company("Allowed")
		blocked = self._company("Blocked")
		self._permit_only(user, allowed)
		frappe.set_user(user)

		with self.assertRaises(frappe.ValidationError):
			save_session_defaults("")
		with self.assertRaises(frappe.ValidationError):
			save_session_defaults(None)

		self.assertEqual(get_permitted_companies(user), [allowed])
		with self.assertRaises(frappe.PermissionError):
			save_session_defaults(blocked)
		self.assertIsNone(get_personal_company(user))

	def _system_user(self) -> str:
		return self._user(user_type="System User", roles=["System Manager"])

	def _user(self, user_type: str, roles: list[str] | None = None) -> str:
		email = f"session.defaults.{frappe.generate_hash(length=8)}@example.com"
		doc = {
			"doctype": "User",
			"email": email,
			"first_name": "Session",
			"user_type": user_type,
			"send_welcome_email": 0,
		}
		if roles:
			doc["roles"] = [{"role": role} for role in roles]
		user = frappe.get_doc(doc).insert(ignore_permissions=True)
		self._users.append(user.name)
		return user.name

	def _company(self, label: str) -> str:
		suffix = frappe.generate_hash(length=5).upper()
		name = f"SD {label} {suffix}"
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": name,
				"abbr": suffix[:5],
				"default_currency": "PHP",
				"country": "Philippines",
			}
		).insert(ignore_permissions=True)
		return name

	def _dimension_user(self) -> str:
		return self._user(
			user_type="System User",
			roles=["System Manager", "Accounts Manager", "HR Manager"],
		)

	def _branch(self, company: str) -> str:
		label = f"SDB{frappe.generate_hash(length=6)}"
		data = {"doctype": "Branch", "branch": label}
		meta = frappe.get_meta("Branch")
		if meta.has_field("custom_company"):
			data["custom_company"] = company
		elif meta.has_field("company"):
			data["company"] = company
		doc = frappe.get_doc(data)
		doc.insert(ignore_permissions=True)
		return doc.name

	def _leaf_cost_center(self, company: str) -> str:
		name = frappe.db.get_value(
			"Cost Center",
			{"company": company, "is_group": 0, "disabled": 0},
			"name",
		)
		self.assertTrue(name)
		return name

	def _profit_center(self, company: str) -> str:
		code = frappe.generate_hash(length=8).upper()
		frappe.get_doc(
			{
				"doctype": "Profit Center",
				"code": code,
				"description": code,
				"company": company,
			}
		).insert(ignore_permissions=True)
		return code

	def _permit_only(self, user: str, company: str) -> None:
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user,
				"allow": "Company",
				"for_value": company,
				"apply_to_all_doctypes": 1,
			}
		).insert(ignore_permissions=True)
