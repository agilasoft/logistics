# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from logistics.special_projects.special_project_charge_lifecycle import (
	append_charge_lifecycle_tag_for_test,
	normalize_lifecycle_job_order_job_fields,
	sync_lifecycle_job_execution_no,
)
from logistics.special_projects.test_special_project_helpers import (
	new_special_project_for_test,
)


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
		normalize_lifecycle_job_order_job_fields(frappe._dict(lifecycle_jobs=[row]))
		self.assertEqual(row.job_type, "Air Booking")
		self.assertEqual(row.order_no, "AB-LEGACY-1")
		self.assertIsNone(row.job_no)

	def test_save_clears_legacy_execution_job_type_on_planning_row(self):
		sp = new_special_project_for_test("Test Legacy Lifecycle Job Type")
		if not sp:
			self.skipTest("Company, Customer, and Cost Center required")

		sp.append("lifecycle_jobs", {"service_type": "Air", "activity_name": "Air leg"})
		sp.insert(ignore_permissions=True)
		row_name = sp.lifecycle_jobs[0].name
		frappe.db.set_value(
			"Lifecycle Job",
			row_name,
			{"job_type": "Transport Job", "job_no": None},
			update_modified=False,
		)
		sp.reload()
		sp.save(ignore_permissions=True)
		sp.reload()
		row = sp.lifecycle_jobs[0]
		self.assertFalse((row.job_type or "").strip())
		self.assertFalse((row.job_no or "").strip())

	def test_charge_row_tags_lifecycle_line(self):
		sp = new_special_project_for_test("Test Charge Lifecycle Tag")
		if not sp:
			self.skipTest("Company, Customer, and Cost Center required")
		if not frappe.get_meta("Special Project Charges").has_field("lifecycle_job_line"):
			self.skipTest("lifecycle_job_line not installed on Special Project Charges")

		sp.append("lifecycle_jobs", {"service_type": "Transport", "activity_name": "Leg 1"})
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
		line = sp.lifecycle_jobs[0]
		append_charge_lifecycle_tag_for_test(sp, sp.charges[0].idx, line.name)
		sp.save(ignore_permissions=True)
		sp.reload()
		self.assertEqual(sp.charges[0].lifecycle_job_line, line.name)
