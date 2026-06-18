# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from logistics.special_projects.lifecycle_job_planned_rollup import (
	sync_lifecycle_job_planned_from_charges,
)
from logistics.special_projects.test_special_project_helpers import (
	new_special_project_for_test,
)


class TestChargeLifecycleTagRollup(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._has_charge_tag = bool(
			frappe.get_meta("Special Project Charges").has_field("lifecycle_job_line")
		)

	def setUp(self):
		if not self._has_charge_tag:
			self.skipTest("lifecycle_job_line not installed")

	def _new_special_project(self):
		sp = new_special_project_for_test("Test Charge LC Tag Rollup")
		if not sp:
			self.skipTest("Company, Customer, and Cost Center required")
		return sp

	def test_one_charge_tags_one_lifecycle_row(self):
		sp = self._new_special_project()
		sp.append("lifecycle_jobs", {"service_type": "Air", "activity_name": "Air 1"})
		sp.append("lifecycle_jobs", {"service_type": "Air", "activity_name": "Air 2"})
		sp.insert(ignore_permissions=True)
		sp.reload()
		sp.append(
			"charges",
			{
				"service_type": "Air",
				"description": "Handling In",
				"estimated_cost": 300,
				"estimated_revenue": 600,
				"lifecycle_job_line": sp.lifecycle_jobs[0].name,
			},
		)
		sp.save(ignore_permissions=True)
		sp.reload()
		self.assertEqual(sp.lifecycle_jobs[0].planned_cost, 300)
		self.assertEqual(sp.lifecycle_jobs[0].planned_revenue, 600)
		self.assertEqual(sp.lifecycle_jobs[1].planned_cost or 0, 0)

	def test_duplicate_service_type_requires_tag_on_save(self):
		sp = self._new_special_project()
		sp.append("lifecycle_jobs", {"service_type": "Transport", "activity_name": "T1"})
		sp.append("lifecycle_jobs", {"service_type": "Transport", "activity_name": "T2"})
		sp.insert(ignore_permissions=True)
		sp.reload()
		sp.append(
			"charges",
			{
				"service_type": "Transport",
				"description": "Shared",
				"estimated_cost": 100,
			},
		)
		with self.assertRaises(frappe.ValidationError):
			sp.save(ignore_permissions=True)
