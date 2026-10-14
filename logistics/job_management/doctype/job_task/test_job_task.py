# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Job Task template resolution and populate rules. No database."""

from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from logistics.doc_event_hooks import DOC_EVENTS
from logistics.job_management.doctype.job_task.job_task import JobTask
from logistics.job_management.job_task import (
	DEFAULT_TASKS,
	JOB_TASK_PARENTS,
	_populate_job_tasks,
	choose_job_task_template,
	tasks_to_insert,
)

HANDLER = "logistics.job_management.job_task.ensure_job_tasks_from_template"


class _Meta:
	def __init__(self, fields):
		self._fields = set(fields)

	def has_field(self, name):
		return name in self._fields


class _Parent:
	def __init__(self):
		self.doctype = "Transport Job"
		self.name = "TRJ-00001"
		self.meta = _Meta({"job_number"})
		self.direction = ""
		self.entry_type = ""
		self.job_number = "JN-TRJ-00001"

	def get(self, fieldname):
		return getattr(self, fieldname, None)


class _TaskDoc:
	def __init__(self, data, inserted, existing):
		self.data = data
		self._inserted = inserted
		self._existing = existing

	def insert(self, ignore_permissions=False):
		self._inserted.append(dict(self.data))
		self._existing.append(
			{
				"name": "JT-{0}".format(len(self._inserted)),
				"task_code": self.data["task_code"],
				"status": self.data["status"],
			}
		)


class TestJobTask(UnitTestCase):
	def test_resolution_prefers_doctype_specific_default(self):
		chosen = choose_job_task_template(
			"Transport Job",
			[
				{
					"name": "Generic Transport",
					"applies_to_doctype": "",
					"is_default": 1,
					"direction": "",
					"entry_type": "",
				},
				{
					"name": "Transport Job Extra",
					"applies_to_doctype": "Transport Job",
					"is_default": 0,
					"direction": "",
					"entry_type": "",
				},
				{
					"name": "Sea Shipment Tasks",
					"applies_to_doctype": "Sea Shipment",
					"is_default": 1,
					"direction": "",
					"entry_type": "",
				},
				{
					"name": "Transport Job Tasks",
					"applies_to_doctype": "Transport Job",
					"is_default": 1,
					"direction": "",
					"entry_type": "",
				},
			],
		)
		self.assertEqual(chosen["name"], "Transport Job Tasks")

	def test_populate_creates_tasks_once_and_keeps_status(self):
		parent = _Parent()
		existing = []
		inserted = []
		items = [
			{
				"task_code": "CONFIRM_PICKUP",
				"subject": "Confirm pickup",
				"description": "Confirm the pickup window.",
				"sequence": 10,
				"is_required": 1,
				"assignee_role": None,
			},
			{
				"task_code": "CLOSE_JOB",
				"subject": "Close job",
				"description": "Close the job.",
				"sequence": 20,
				"is_required": 1,
				"assignee_role": None,
			},
		]

		def get_all(doctype, **kwargs):
			if doctype == "Job Task Template":
				return [
					{
						"name": "Transport Job Tasks",
						"is_default": 1,
						"applies_to_doctype": "Transport Job",
						"direction": "",
						"entry_type": "",
					}
				]
			if doctype == "Job Task Template Item":
				return list(items)
			if doctype == "Job Task":
				return list(existing)
			raise AssertionError(doctype)

		def get_doc(data):
			self.assertIsInstance(data, dict)
			return _TaskDoc(data, inserted, existing)

		with (
			patch("logistics.job_management.job_task.frappe.get_all", side_effect=get_all),
			patch("logistics.job_management.job_task.frappe.get_doc", side_effect=get_doc),
		):
			first = _populate_job_tasks(
				"Transport Job", "TRJ-00001", doc=parent, check_permission=False
			)
			existing[0]["status"] = "In Progress"
			second = _populate_job_tasks(
				"Transport Job", "TRJ-00001", doc=parent, check_permission=False
			)

		self.assertEqual(first["added"], 2)
		self.assertEqual(first["template"], "Transport Job Tasks")
		self.assertEqual(second["added"], 0)
		self.assertEqual(len(inserted), 2)
		self.assertEqual([row["status"] for row in inserted], ["Open", "Open"])
		self.assertEqual(inserted[0]["job_number"], "JN-TRJ-00001")
		self.assertEqual(existing[0]["status"], "In Progress")
		self.assertEqual(
			[row["task_code"] for row in tasks_to_insert(existing, items)],
			[],
		)

	def test_populate_ignores_doctype_outside_registry(self):
		with patch("logistics.job_management.job_task.frappe.get_all") as get_all:
			result = _populate_job_tasks("Customer", "CUST-0001", check_permission=False)
		get_all.assert_not_called()
		self.assertEqual(result["added"], 0)
		self.assertIn("not used", str(result["message"]).lower())

	def test_every_parent_has_a_short_checklist_and_a_desk_button(self):
		self.assertEqual(set(DEFAULT_TASKS), set(JOB_TASK_PARENTS))
		for doctype, tasks in DEFAULT_TASKS.items():
			self.assertGreaterEqual(len(tasks), 4, doctype)
			self.assertLessEqual(len(tasks), 6, doctype)
			codes = [task["task_code"] for task in tasks]
			self.assertEqual(len(codes), len(set(codes)), doctype)

		script = Path(__file__).resolve().parents[3].joinpath("public", "js", "job_task.js").read_text()
		for doctype in JOB_TASK_PARENTS:
			self.assertIn('"{0}"'.format(doctype), script)
			events = DOC_EVENTS[doctype]["after_insert"]
			if isinstance(events, list):
				self.assertIn(HANDLER, events)
			else:
				self.assertEqual(events, HANDLER)

	def test_unknown_parent_is_rejected(self):
		task = JobTask.__new__(JobTask)
		task.job_type = "Customer"
		with patch(
			"logistics.job_management.doctype.job_task.job_task.frappe.throw",
			side_effect=frappe.ValidationError("no"),
		):
			with self.assertRaises(frappe.ValidationError):
				task._require_known_parent()
