# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
import unittest

from logistics.job_management.cost_center_defaults import (
	default_branch_for_company,
	set_cost_center_branch_default,
)


class TestCostCenterDefaults(unittest.TestCase):
	def test_default_branch_for_company_returns_existing_branch(self):
		branch = frappe.db.get_value("Branch", {}, "name", order_by="creation asc")
		if not branch:
			self.skipTest("No Branch records in site")

		self.assertEqual(default_branch_for_company(), branch)

	def test_set_cost_center_branch_default_populates_custom_branch(self):
		cc_meta = frappe.get_meta("Cost Center")
		if not cc_meta.has_field("custom_branch"):
			self.skipTest("Cost Center has no custom_branch field")

		branch = default_branch_for_company()
		if not branch:
			self.skipTest("No Branch records in site")

		doc = frappe.new_doc("Cost Center")
		doc.cost_center_name = f"Test CC Branch Default {frappe.generate_hash(length=6)}"
		doc.company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value(
			"Company", {}, "name"
		)
		doc.is_group = 1
		set_cost_center_branch_default(doc)
		self.assertEqual(doc.custom_branch, branch)
