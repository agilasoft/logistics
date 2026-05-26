# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime

from logistics.special_projects.lifecycle_job_planned_rollup import (
	sync_lifecycle_job_planned_from_charges,
)


class TestLifecycleJobPlannedRollup(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._has_lifecycle_jobs = bool(
			frappe.get_meta("Special Project").has_field("lifecycle_jobs")
		)
		cls._has_lifecycle_job_row = bool(
			frappe.get_meta("Special Project Charges").has_field("lifecycle_job_row")
		)

	def setUp(self):
		if not self._has_lifecycle_jobs or not self._has_lifecycle_job_row:
			self.skipTest("lifecycle_jobs / lifecycle_job_row not installed")

	def _new_special_project(self):
		company = frappe.db.get_value("Company", {}, "name")
		customer = frappe.db.get_value("Customer", {"disabled": 0}, "name")
		if not company or not customer:
			self.skipTest("Company and Customer required")
		sp = frappe.new_doc("Special Project")
		sp.project_name = f"Test Lifecycle Planned Rollup {now_datetime()}"
		sp.customer = customer
		sp.company = company
		return sp

	def test_two_air_rows_get_distinct_planned_totals(self):
		sp = self._new_special_project()
		sp.append("lifecycle_jobs", {"service_type": "Air", "activity_name": "Air 1"})
		sp.append("lifecycle_jobs", {"service_type": "Air", "activity_name": "Air 2"})
		sp.append(
			"charges",
			{
				"service_type": "Air",
				"lifecycle_job_row": 1,
				"description": "Air 1 cost",
				"estimated_cost": 100,
				"estimated_revenue": 200,
			},
		)
		sp.append(
			"charges",
			{
				"service_type": "Air",
				"lifecycle_job_row": 2,
				"description": "Air 2 cost",
				"estimated_cost": 50,
				"estimated_revenue": 80,
			},
		)
		sp.insert(ignore_permissions=True)

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

	def test_auto_assign_when_single_lifecycle_row_for_service_type(self):
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
		self.assertEqual(sp.charges[0].lifecycle_job_row, sp.lifecycle_jobs[0].idx)
		self.assertEqual(sp.lifecycle_jobs[0].planned_cost, 30)
		self.assertEqual(sp.lifecycle_jobs[0].planned_revenue, 60)

	def test_sync_helper_excludes_disbursement(self):
		sp = self._new_special_project()
		sp.append("lifecycle_jobs", {"service_type": "Transport", "activity_name": "Leg"})
		sp.append(
			"charges",
			{
				"service_type": "Transport",
				"lifecycle_job_row": 1,
				"charge_type": "Disbursement",
				"estimated_cost": 999,
				"estimated_revenue": 999,
			},
		)
		sync_lifecycle_job_planned_from_charges(sp)
		self.assertEqual(sp.lifecycle_jobs[0].planned_cost, 0)
		self.assertEqual(sp.lifecycle_jobs[0].planned_revenue, 0)

	def test_auto_assign_when_single_planning_row_among_duplicates(self):
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
			{"service_type": "Special Project", "activity_name": "Equipment"},
		)
		sp.append(
			"charges",
			{
				"service_type": "Special Project",
				"description": "Vehicle Rental",
				"estimated_cost": 100,
				"estimated_revenue": 150,
			},
		)
		sp.insert(ignore_permissions=True, ignore_links=True)
		self.assertEqual(sp.charges[0].lifecycle_job_row, sp.lifecycle_jobs[1].idx)
		self.assertEqual(sp.lifecycle_jobs[1].planned_cost, 100)
		self.assertEqual(sp.lifecycle_jobs[1].planned_revenue, 150)

	def test_saves_without_lifecycle_job_row_when_duplicate_service_type(self):
		sp = self._new_special_project()
		sp.append("lifecycle_jobs", {"service_type": "Air", "activity_name": "A"})
		sp.append("lifecycle_jobs", {"service_type": "Air", "activity_name": "B"})
		sp.append(
			"charges",
			{
				"service_type": "Air",
				"description": "Unassigned",
				"estimated_cost": 10,
				"estimated_revenue": 20,
			},
		)
		sp.insert(ignore_permissions=True, ignore_links=True)
