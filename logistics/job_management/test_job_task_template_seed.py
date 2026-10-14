# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Default Job Task Template seeding skips DocTypes the site does not have."""

from __future__ import annotations

import unittest

from logistics.job_management.job_task_template_seed import parents_to_seed


PARENTS = {
	"MICE Job": ("MICE", "Shipment/Job"),
	"Exhibit Job": ("Exhibits", "Shipment/Job"),
	"Time Sensitive Case": ("General", "Shipment/Job"),
}

TASKS = {
	"MICE Job": ({"task_code": "CONFIRM_SCOPE", "subject": "Confirm scope"},),
	"Exhibit Job": ({"task_code": "CONFIRM_SCOPE", "subject": "Confirm exhibit scope"},),
	"Time Sensitive Case": ({"task_code": "ACKNOWLEDGE", "subject": "Acknowledge case"},),
}


class TestJobTaskTemplateSeed(unittest.TestCase):
	def test_missing_doctype_is_skipped_and_later_parents_are_kept(self):
		specs, skipped = parents_to_seed(
			PARENTS,
			TASKS,
			installed_doctypes=["MICE Job", "Time Sensitive Case"],
			existing_defaults=[],
			existing_names=[],
		)
		self.assertEqual(skipped, ["Exhibit Job"])
		self.assertEqual(
			[spec["doctype"] for spec in specs],
			["MICE Job", "Time Sensitive Case"],
		)
		self.assertEqual(specs[0]["template_name"], "MICE Job Tasks")
		self.assertEqual(specs[0]["product_type"], "MICE")
		self.assertEqual(specs[0]["applies_to"], "Shipment/Job")
		self.assertEqual(specs[0]["tasks"][0]["task_code"], "CONFIRM_SCOPE")

	def test_installed_exhibit_job_is_seeded(self):
		specs, skipped = parents_to_seed(
			PARENTS,
			TASKS,
			installed_doctypes=list(PARENTS),
			existing_defaults=[],
			existing_names=[],
		)
		self.assertEqual(skipped, [])
		self.assertIn("Exhibit Job", [spec["doctype"] for spec in specs])

	def test_existing_default_and_taken_name_are_not_seeded_again(self):
		specs, skipped = parents_to_seed(
			PARENTS,
			TASKS,
			installed_doctypes=list(PARENTS),
			existing_defaults=["MICE Job"],
			existing_names=["Exhibit Job Tasks"],
		)
		self.assertEqual(skipped, [])
		self.assertEqual([spec["doctype"] for spec in specs], ["Time Sensitive Case"])

	def test_parent_without_tasks_is_not_seeded(self):
		specs, skipped = parents_to_seed(
			PARENTS,
			{"MICE Job": TASKS["MICE Job"]},
			installed_doctypes=list(PARENTS),
			existing_defaults=[],
			existing_names=[],
		)
		self.assertEqual(skipped, [])
		self.assertEqual([spec["doctype"] for spec in specs], ["MICE Job"])
