# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests import UnitTestCase

from logistics.mice.mice_project_lifecycle import (
	clear_missing_lifecycle_job_stages,
	validate_lifecycle_stage_advance,
)


class TestExhibitLifecycle(UnitTestCase):
	def test_lifecycle_advance_blocked_when_activities_incomplete(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("Exhibit not installed")
		customer = frappe.db.get_value("Customer", {}, "name")
		if not customer:
			self.skipTest("No Customer")
		organizer_name = "Lifecycle Test Organizer"
		organizer = frappe.db.get_value(
			"MICE Organizer", {"organizer_name": organizer_name}, "name"
		)
		if not organizer:
			org_doc = frappe.new_doc("MICE Organizer")
			org_doc.organizer_name = organizer_name
			org_doc.organizer_type = "Company"
			org_doc.customer = customer
			org_doc.insert(ignore_permissions=True)
			organizer = org_doc.name
		frappe.db.set_single_value("MICE Settings", "strict_lifecycle_mode", 1)
		doc = frappe.new_doc("MICE Project")
		doc.project_name = "Lifecycle Validation Test"
		doc.organizer = organizer
		doc.insert(ignore_permissions=True)
		doc.reload()
		doc.lifecycle_stage = "Logistics"
		with self.assertRaises(frappe.ValidationError):
			validate_lifecycle_stage_advance(doc)
		doc.delete(ignore_permissions=True)

	def test_missing_lifecycle_job_stage_is_cleared(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("Exhibit not installed")
		doc = frappe.new_doc("MICE Project")
		doc.append(
			"lifecycle_jobs",
			{
				"service_type": "MICE",
				"lifecycle_stage": "Not A Real Lifecycle Stage",
				"activity_code": "freight_coordination",
				"activity_name": "Freight Coordination",
				"lifecycle_activity_status": "Not Started",
			},
		)
		clear_missing_lifecycle_job_stages(doc)
		row = doc.lifecycle_jobs[0]
		self.assertFalse(row.lifecycle_stage)
		self.assertEqual(row.activity_code, "freight_coordination")
		self.assertEqual(row.activity_name, "Freight Coordination")
		self.assertEqual(len(doc.lifecycle_jobs), 1)

	def test_existing_lifecycle_job_stage_is_kept(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("Exhibit not installed")
		if not frappe.db.exists("DocType", "Lifecycle Stage"):
			self.skipTest("Lifecycle Stage not installed")
		stage = frappe.db.get_value("Lifecycle Stage", {}, "name")
		created = None
		if not stage:
			created = frappe.new_doc("Lifecycle Stage")
			created.lifecycle_stage = "Kept Stage"
			created.for_exhibits = 1
			created.insert(ignore_permissions=True)
			stage = created.name
		try:
			doc = frappe.new_doc("MICE Project")
			doc.append(
				"lifecycle_jobs",
				{
					"service_type": "MICE",
					"lifecycle_stage": stage,
					"activity_code": "freight_coordination",
					"activity_name": "Freight Coordination",
				},
			)
			clear_missing_lifecycle_job_stages(doc)
			self.assertEqual(doc.lifecycle_jobs[0].lifecycle_stage, stage)
			self.assertEqual(doc.lifecycle_jobs[0].activity_code, "freight_coordination")
		finally:
			if created:
				created.delete(ignore_permissions=True)
