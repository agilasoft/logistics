# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from logistics.special_projects.special_project_packages import (
	_delivery_fields_equal,
	_receipt_matches_source,
	autofill_delivery_lifecycle_stages,
	validate_deliveries_read_only,
	validate_packages,
)
from logistics.special_projects.test_special_project_helpers import (
	new_special_project_for_test,
)


class TestDeliveryFieldComparison(UnitTestCase):
	def test_receipt_date_string_vs_date_equal(self):
		old = frappe._dict(receipt_date="2026-06-03")
		new = frappe._dict(receipt_date=frappe.utils.getdate("2026-06-03"))
		self.assertTrue(_delivery_fields_equal(old, new, "receipt_date"))

	def test_receipt_matches_source_job_fields(self):
		rc = frappe._dict(
			source_job_type="Transport Order",
			source_job_no="TRO-1",
			source_doctype="",
			source_name="",
		)
		self.assertTrue(_receipt_matches_source(rc, "Transport Order", "TRO-1"))


class TestDeliveriesReadOnly(IntegrationTestCase):
	def _new_special_project(self):
		sp = new_special_project_for_test("Test Deliveries RO")
		if not sp:
			self.skipTest("Company, Customer, and Cost Center required")
		sp.append(
			"packages",
			{"description": "Crate", "qty_required": 10},
		)
		return sp

	def test_blocks_manual_delivery_on_insert(self):
		sp = self._new_special_project()
		sp.append(
			"deliveries",
			{
				"description": "Crate",
				"qty_received": 1,
				"status": "Posted",
			},
		)
		with self.assertRaises(frappe.ValidationError):
			validate_deliveries_read_only(sp)

	def test_allows_system_post_flag(self):
		sp = self._new_special_project()
		sp.insert(ignore_permissions=True)
		sp.flags.ignore_delivery_validation = True
		sp.append(
			"deliveries",
			{
				"description": "Crate",
				"qty_received": 1,
				"status": "Posted",
				"source_doctype": "Transport Order",
				"source_name": "TEST-TRO",
			},
		)
		validate_deliveries_read_only(sp)

	def test_allows_lifecycle_stage_autofill_after_read_only_check(self):
		sp = self._new_special_project()
		sp.flags.ignore_delivery_validation = True
		sp.append(
			"deliveries",
			{
				"description": "Crate",
				"qty_received": 1,
				"status": "Posted",
				"source_doctype": "Transport Order",
				"source_name": "TEST-TRO",
			},
		)
		sp.insert(ignore_permissions=True)
		sp.flags.ignore_delivery_validation = False
		sp.reload()
		validate_packages(sp)
		validate_deliveries_read_only(sp)
		autofill_delivery_lifecycle_stages(sp)
		self.assertTrue(any((getattr(r, "lifecycle_stage", None) or "").strip() for r in sp.deliveries))

	def test_edit_error_includes_source_job_and_action(self):
		sp = self._new_special_project()
		sp.insert(ignore_permissions=True)
		sp.flags.ignore_delivery_validation = True
		sp.append(
			"deliveries",
			{
				"description": "Crate",
				"qty_received": 1,
				"status": "Posted",
				"source_doctype": "Transport Order",
				"source_name": "TEST-TRO-001",
			},
		)
		sp.save(ignore_permissions=True)
		sp.flags.ignore_delivery_validation = False
		before = frappe.get_doc("Special Project", sp.name)
		sp = frappe.get_doc("Special Project", sp.name)
		sp.deliveries[0].qty_received = 2
		sp._doc_before_save = before
		with self.assertRaises(frappe.ValidationError) as ctx:
			validate_deliveries_read_only(sp)
		self.assertIn("Transport Order", str(ctx.exception))
		self.assertIn("TEST-TRO-001", str(ctx.exception))
		self.assertIn("Qty Received", str(ctx.exception))
		self.assertTrue(frappe.local.message_log)
		last = frappe.local.message_log[-1]
		self.assertEqual(last.primary_action["client_action"], "logistics.special_project_modals.open_source_job")
		self.assertEqual(last.primary_action["args"]["doctype"], "Transport Order")
		self.assertEqual(last.primary_action["args"]["docname"], "TEST-TRO-001")

	def test_ignores_changes_on_cancelled_delivery_rows(self):
		sp = self._new_special_project()
		sp.insert(ignore_permissions=True)
		sp.flags.ignore_delivery_validation = True
		sp.append(
			"deliveries",
			{
				"description": "Crate",
				"qty_received": 1,
				"status": "Cancelled",
				"receipt_date": "2026-06-01",
				"source_doctype": "Transport Order",
				"source_name": "TEST-TRO-CXL",
			},
		)
		sp.save(ignore_permissions=True)
		sp.flags.ignore_delivery_validation = False
		before = frappe.get_doc("Special Project", sp.name)
		sp = frappe.get_doc("Special Project", sp.name)
		sp.deliveries[0].receipt_date = "2026-06-03"
		sp._doc_before_save = before
		validate_deliveries_read_only(sp)
