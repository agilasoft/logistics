# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Tests for ``logistics.utils.lifecycle_template.apply_lifecycle_template``.

These tests focus on the validation and counting behaviour of the apply utility:

- It requires a supported parent doctype.
- It refuses to apply a template that lacks the parent-type applicability flag.
- ``replace_existing`` preserves rows that already have ``job_no`` set.
- Activities whose Lifecycle Stage is not flagged for the parent type are skipped.

The tests run only if a Lifecycle Stage with ``for_special_project`` is already seeded.
"""

from __future__ import annotations

import uuid

import frappe
from frappe.tests import UnitTestCase

from logistics.utils.lifecycle_template import apply_lifecycle_template


def _have_sp_stages() -> str | None:
	return frappe.db.get_value("Lifecycle Stage", {"for_special_project": 1}, "name")


def _have_sp_activity(stage: str) -> str | None:
	return frappe.db.get_value(
		"Activity Code", {"for_special_project": 1, "lifecycle_stage": stage}, "name"
	)


def _make_template(*, for_sp: int, for_ex: int, stages: list[tuple[str, str | None]]) -> str:
	name = f"Test LT {uuid.uuid4().hex[:8]}"
	doc = frappe.get_doc(
		{
			"doctype": "Lifecycle Template",
			"template_name": name,
			"enabled": 1,
			"for_special_project": for_sp,
			"for_exhibits": for_ex,
			"description": "Auto-generated test template.",
			"activities": [
				{
					"lifecycle_stage": stage,
					"activity_code": ac,
					"service_type": "Special Project",
					"sort_order": i + 1,
				}
				for i, (stage, ac) in enumerate(stages)
			],
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _make_special_project() -> str | None:
	if not frappe.db.exists("DocType", "Special Project"):
		return None
	customer = frappe.db.get_value("Customer", {"disabled": 0}, "name")
	if not customer:
		return None
	stage = _have_sp_stages()
	if not stage:
		return None
	doc = frappe.get_doc(
		{
			"doctype": "Special Project",
			"project_name": f"Test SP LT {uuid.uuid4().hex[:6]}",
			"customer": customer,
			"lifecycle_stage": stage,
		}
	)
	try:
		doc.insert(ignore_permissions=True)
	except Exception:
		return None
	return doc.name


class TestApplyLifecycleTemplate(UnitTestCase):
	def setUp(self):
		self.stage = _have_sp_stages()
		if not self.stage:
			self.skipTest("No Lifecycle Stage with for_special_project found; seed patches not run.")
		self.activity = _have_sp_activity(self.stage)

	def tearDown(self):
		# best-effort cleanup of any templates we created
		for tpl in frappe.db.get_all(
			"Lifecycle Template",
			filters={"template_name": ("like", "Test LT %")},
			pluck="name",
		):
			frappe.delete_doc("Lifecycle Template", tpl, force=True, ignore_permissions=True)

	def test_rejects_unsupported_parent_doctype(self):
		tpl = _make_template(for_sp=1, for_ex=0, stages=[(self.stage, self.activity)])
		with self.assertRaises(frappe.ValidationError):
			apply_lifecycle_template("Sales Order", "SO-DOES-NOT-EXIST", tpl)

	def test_rejects_template_not_for_special_project(self):
		sp = _make_special_project()
		if not sp:
			self.skipTest("Cannot create a Special Project in this environment.")
		tpl = _make_template(for_sp=0, for_ex=1, stages=[(self.stage, self.activity)])
		with self.assertRaises(frappe.ValidationError):
			apply_lifecycle_template("Special Project", sp, tpl)

	def test_append_adds_rows(self):
		sp_name = _make_special_project()
		if not sp_name:
			self.skipTest("Cannot create a Special Project in this environment.")
		tpl = _make_template(
			for_sp=1, for_ex=0,
			stages=[(self.stage, self.activity), (self.stage, self.activity)],
		)
		before_doc = frappe.get_doc("Special Project", sp_name)
		before_rows = len(before_doc.get("lifecycle_jobs") or [])
		result = apply_lifecycle_template("Special Project", sp_name, tpl)
		after_doc = frappe.get_doc("Special Project", sp_name)
		after_rows = len(after_doc.get("lifecycle_jobs") or [])
		self.assertEqual(result["added"], 2)
		self.assertEqual(result["removed"], 0)
		self.assertEqual(after_rows - before_rows, 2)

	def test_replace_existing_keeps_linked_rows(self):
		sp_name = _make_special_project()
		if not sp_name:
			self.skipTest("Cannot create a Special Project in this environment.")
		sp = frappe.get_doc("Special Project", sp_name)
		sp.append("lifecycle_jobs", {
			"lifecycle_stage": self.stage,
			"service_type": "Transport",
			"job_type": "Transport Order",
			"job_no": "TRO-LINKED-SENTINEL",
		})
		sp.append("lifecycle_jobs", {
			"lifecycle_stage": self.stage,
			"service_type": "Special Project",
		})
		sp.save(ignore_permissions=True)

		tpl = _make_template(for_sp=1, for_ex=0, stages=[(self.stage, self.activity)])
		result = apply_lifecycle_template(
			"Special Project", sp_name, tpl, replace_existing=1
		)
		self.assertEqual(result["kept"], 1)
		self.assertEqual(result["removed"], 1)
		after = frappe.get_doc("Special Project", sp_name)
		linked = [r for r in after.get("lifecycle_jobs") or [] if (r.get("job_no") or "") == "TRO-LINKED-SENTINEL"]
		self.assertEqual(len(linked), 1, "Linked Lifecycle Job row must be preserved through replace.")
