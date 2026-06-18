# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from logistics.special_projects.lifecycle_job_planned_rollup import (
	sync_lifecycle_job_planned_from_charges,
)
from logistics.special_projects.special_project_charge_lifecycle import (
	append_charge_lifecycle_tag_for_test,
)
from logistics.special_projects.test_special_project_helpers import (
	new_special_project_for_test,
)


class TestLifecycleJobPlannedRollup(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._has_lifecycle_jobs = bool(
			frappe.get_meta("Special Project").has_field("lifecycle_jobs")
		)
		cls._has_charge_tag = bool(
			frappe.get_meta("Special Project Charges").has_field("lifecycle_job_line")
		)

	def setUp(self):
		if not self._has_lifecycle_jobs or not self._has_charge_tag:
			self.skipTest("lifecycle_jobs / lifecycle_job_line not installed")

	def _new_special_project(self):
		sp = new_special_project_for_test("Test Lifecycle Planned Rollup")
		if not sp:
			self.skipTest("Company, Customer, and Cost Center required")
		return sp

	def test_two_air_rows_get_distinct_planned_totals(self):
		sp = self._new_special_project()
		sp.append("lifecycle_jobs", {"service_type": "Air", "activity_name": "Air 1"})
		sp.append("lifecycle_jobs", {"service_type": "Air", "activity_name": "Air 2"})
		sp.insert(ignore_permissions=True)
		sp.reload()
		sp.append(
			"charges",
			{
				"service_type": "Air",
				"description": "Air 1 cost",
				"estimated_cost": 100,
				"estimated_revenue": 200,
				"lifecycle_job_line": sp.lifecycle_jobs[0].name,
			},
		)
		sp.append(
			"charges",
			{
				"service_type": "Air",
				"description": "Air 2 cost",
				"estimated_cost": 50,
				"estimated_revenue": 80,
				"lifecycle_job_line": sp.lifecycle_jobs[1].name,
			},
		)
		sp.save(ignore_permissions=True)
		sp.reload()

		row1, row2 = sp.lifecycle_jobs[0], sp.lifecycle_jobs[1]
		self.assertEqual(row1.planned_cost, 100)
		self.assertEqual(row1.planned_revenue, 200)
		self.assertEqual(row2.planned_cost, 50)
		self.assertEqual(row2.planned_revenue, 80)

		sp.reload()
		total_planned_cost = sum((r.planned_cost or 0) for r in sp.lifecycle_jobs)
		total_planned_revenue = sum((r.planned_revenue or 0) for r in sp.lifecycle_jobs)
		self.assertEqual(total_planned_cost, 150)
		self.assertEqual(total_planned_revenue, 280)

	def test_single_lifecycle_row_implicit_attribution_by_service_type(self):
		sp = self._new_special_project()
		sp.append("lifecycle_jobs", {"service_type": "Special Project", "activity_name": "Phase A"})
		sp.append(
			"charges",
			{
				"service_type": "Special Project",
				"description": "SP line",
				"estimated_cost": 30,
				"estimated_revenue": 60,
			},
		)
		sp.insert(ignore_permissions=True)
		self.assertEqual(sp.lifecycle_jobs[0].planned_cost, 30)
		self.assertEqual(sp.lifecycle_jobs[0].planned_revenue, 60)

	def test_sync_helper_excludes_disbursement(self):
		sp = self._new_special_project()
		sp.append("lifecycle_jobs", {"service_type": "Transport", "activity_name": "Leg"})
		sp.append(
			"charges",
			{
				"service_type": "Transport",
				"charge_type": "Disbursement",
				"estimated_cost": 999,
				"estimated_revenue": 999,
			},
		)
		sync_lifecycle_job_planned_from_charges(sp)
		self.assertEqual(sp.lifecycle_jobs[0].planned_cost, 0)
		self.assertEqual(sp.lifecycle_jobs[0].planned_revenue, 0)

	def test_implicit_attribution_when_single_planning_row_among_duplicates(self):
		sp = self._new_special_project()
		sp.append(
			"lifecycle_jobs",
			{
				"service_type": "Special Project",
				"activity_name": "On-site",
				"job_no": "PJ-1",
				"job_type": "Project Job",
			},
		)
		sp.append(
			"lifecycle_jobs",
			{
				"service_type": "Special Project",
				"activity_name": "Equipment",
				"sp_handling": "Rigging",
			},
		)
		sp.append(
			"charges",
			{
				"service_type": "Special Project",
				"description": "Vehicle Rental",
				"sp_handling": "Rigging",
				"estimated_cost": 100,
				"estimated_revenue": 150,
			},
		)
		sp.insert(ignore_permissions=True, ignore_links=True)
		self.assertEqual(sp.lifecycle_jobs[1].planned_cost, 100)
		self.assertEqual(sp.lifecycle_jobs[1].planned_revenue, 150)

	def test_wildcard_charge_matches_rows_sharing_default_params(self):
		sp = self._new_special_project()
		sp.append("lifecycle_jobs", {"service_type": "Air", "activity_name": "A"})
		sp.append("lifecycle_jobs", {"service_type": "Air", "activity_name": "B"})
		sp.insert(ignore_permissions=True)
		sp.reload()
		sp.append(
			"charges",
			{
				"service_type": "Air",
				"description": "Wildcard freight",
				"estimated_cost": 10,
				"estimated_revenue": 20,
			},
		)
		sp.save(ignore_permissions=True)
		sp.reload()
		self.assertEqual(sp.lifecycle_jobs[0].planned_cost, 10)
		self.assertEqual(sp.lifecycle_jobs[1].planned_cost, 10)

	def test_two_transport_rows_get_distinct_planned_totals_by_params(self):
		sp = self._new_special_project()
		sp.append(
			"lifecycle_jobs",
			{
				"service_type": "Transport",
				"activity_name": "Leg 1",
				"transport_template": "TPL-1",
				"vehicle_type": "20FT",
			},
		)
		sp.append(
			"lifecycle_jobs",
			{
				"service_type": "Transport",
				"activity_name": "Leg 2",
				"transport_template": "TPL-2",
				"vehicle_type": "40FT",
			},
		)
		sp.append(
			"charges",
			{
				"service_type": "Transport",
				"description": "Leg 1 delivery",
				"transport_template": "TPL-1",
				"vehicle_type": "20FT",
				"estimated_cost": 100,
				"estimated_revenue": 200,
			},
		)
		sp.append(
			"charges",
			{
				"service_type": "Transport",
				"description": "Leg 2 delivery",
				"transport_template": "TPL-2",
				"vehicle_type": "40FT",
				"estimated_cost": 50,
				"estimated_revenue": 80,
			},
		)
		sp.insert(ignore_permissions=True, ignore_links=True)
		sp.reload()
		row1, row2 = sp.lifecycle_jobs[0], sp.lifecycle_jobs[1]
		self.assertEqual(row1.planned_cost, 100)
		self.assertEqual(row1.planned_revenue, 200)
		self.assertEqual(row2.planned_cost, 50)
		self.assertEqual(row2.planned_revenue, 80)
