# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from unittest.mock import patch

from logistics.special_projects.special_project_charge_lifecycle import (
	append_charge_lifecycle_tag_for_test,
	normalize_lifecycle_job_order_job_fields,
	sync_lifecycle_job_execution_no,
)
from logistics.special_projects.test_special_project_helpers import (
	new_special_project_for_test,
)


class TestSyncLifecycleJobExecutionNo(UnitTestCase):
	def test_sets_job_no_from_dict_service_row(self):
		row = {
			"name": "SPS-1",
			"service_type": "Air",
			"job_type": "Air Booking",
			"order_no": "ABK-1",
		}
		with patch(
			"logistics.utils.special_project_internal_jobs._resolve_order_ref_to_operational_ref",
			return_value=("Air Shipment", "ASP-1"),
		):
			sync_lifecycle_job_execution_no(row)
		self.assertEqual(row["job_no"], "ASP-1")


class TestChargeLifecycleTag(IntegrationTestCase):
	def test_sync_clears_job_no_when_it_duplicates_order_no(self):
		row = frappe._dict(
			service_type="Transport",
			job_type="Transport Order",
			order_no="TO-1",
			job_no="TO-1",
		)
		sync_lifecycle_job_execution_no(row)
		self.assertIsNone(row.job_no)

	def test_normalize_legacy_planning_job_type_on_lifecycle_row(self):
		row = frappe._dict(
			service_type="Air",
			job_type="Air Booking",
			job_no="AB-LEGACY-1",
			order_no=None,
		)
		doc = frappe.get_doc({"doctype": "Special Project", "name": "TEST-NORM"})
		doc.__dict__["special_project_services"] = [row]
		doc.flags._special_project_services_from_form = True
		normalize_lifecycle_job_order_job_fields(doc)
		self.assertEqual(row.job_type, "Air Booking")
		self.assertEqual(row.order_no, "AB-LEGACY-1")
		self.assertIsNone(row.job_no)

	def test_save_clears_legacy_execution_job_type_on_planning_row(self):
		sp = new_special_project_for_test("Test Legacy Lifecycle Job Type")
		if not sp:
			self.skipTest("Company, Customer, and Cost Center required")

		sp.append(
			"applicable_lifecycle_stages",
			{"lifecycle_stage": sp.lifecycle_stage or "Pre-Show"},
		)
		sp.append(
			"special_project_services",
			{
				"service_type": "Air",
				"activity_name": "Air leg",
				"lifecycle_stage": sp.lifecycle_stage or "Pre-Show",
			},
		)
		sp.insert(ignore_permissions=True)
		row_name = sp.special_project_services[0].name
		frappe.db.set_value(
			"Special Project Service",
			row_name,
			{"job_type": "Transport Job", "job_no": None},
			update_modified=False,
		)
		sp.reload()
		sp.save(ignore_permissions=True)
		sp.reload()
		row = sp.special_project_services[0]
		self.assertEqual((row.job_type or "").strip(), "Air Booking")
		self.assertFalse((row.job_no or "").strip())

	def test_charge_row_tags_lifecycle_line(self):
		sp = new_special_project_for_test("Test Charge Lifecycle Tag")
		if not sp:
			self.skipTest("Company, Customer, and Cost Center required")
		if not frappe.get_meta("Special Project Charges").has_field("lifecycle_stage"):
			self.skipTest("lifecycle_stage not installed on Special Project Charges")

		stage = sp.lifecycle_stage or "Pre-Show"
		sp.append("applicable_lifecycle_stages", {"lifecycle_stage": stage})
		sp.append(
			"special_project_services",
			{
				"service_type": "Transport",
				"activity_name": "Leg 1",
				"lifecycle_stage": stage,
			},
		)
		sp.append(
			"charges",
			{
				"service_type": "Transport",
				"description": "Delivery",
				"estimated_cost": 50,
			},
		)
		sp.insert(ignore_permissions=True)
		sp.reload()
		append_charge_lifecycle_tag_for_test(sp, sp.charges[0].idx, stage)
		sp.save(ignore_permissions=True)
		sp.reload()
		self.assertEqual(sp.charges[0].lifecycle_stage, stage)
