# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Job Task child-column repair. No database."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from logistics.job_management.job_task_child_schema import (
	DOCTYPE,
	TABLE,
	add_column_clauses,
	missing_child_link_columns,
	relink_statement,
	should_relink_legacy_rows,
	table_exists_argument,
)

# These warehousing documents store their checklist in the same Job Task table.
# A missing parent column breaks every one of them, not only Inbound Order.
WAREHOUSING_JOB_TASK_PARENTS = (
	"Inbound Order",
	"Release Order",
	"Transfer Order",
	"Cross-Docking Order",
	"VAS Order",
	"Stocktake Order",
	"Warehouse Job",
)


class TestJobTaskChildSchema(unittest.TestCase):
	def test_fresh_child_table_needs_no_columns(self):
		columns = ["name", "parent", "parentfield", "parenttype", "task_code", "idx"]
		self.assertEqual(missing_child_link_columns(columns), [])
		self.assertFalse(should_relink_legacy_rows(columns))

	def test_standalone_table_is_missing_the_child_link(self):
		columns = ["name", "job_no", "job_type", "task_code", "idx"]
		self.assertEqual(
			missing_child_link_columns(columns),
			["parent", "parentfield", "parenttype"],
		)
		self.assertFalse(should_relink_legacy_rows(columns))

	def test_legacy_rows_relink_once_the_child_columns_exist(self):
		columns = ["name", "job_no", "job_type", "parent", "parentfield", "parenttype", "sequence"]
		self.assertEqual(missing_child_link_columns(columns), [])
		self.assertTrue(should_relink_legacy_rows(columns))
		statement = relink_statement(has_sequence=True)
		self.assertIn("parent = job_no", statement)
		self.assertIn("parenttype = job_type", statement)
		self.assertIn("parentfield = 'job_tasks'", statement)
		self.assertIn("sequence", statement)
		self.assertIn("IFNULL(parent, '') = ''", statement)

	def test_add_column_clauses_name_only_the_child_link(self):
		clauses = add_column_clauses(["parent", "parentfield"], 140)
		self.assertEqual(
			clauses,
			[
				"ADD COLUMN `parent` varchar(140)",
				"ADD COLUMN `parentfield` varchar(140)",
			],
		)
		with self.assertRaises(ValueError):
			add_column_clauses(["job_no"], 140)

	def test_table_exists_argument_is_the_doctype_not_the_physical_name(self):
		self.assertEqual(table_exists_argument(), DOCTYPE)
		self.assertEqual("tab" + table_exists_argument(), TABLE)
		# frappe.db.table_exists("tabJob Task") looks up tabtabJob Task.
		self.assertNotEqual("tab" + TABLE, TABLE)

	def test_warehousing_documents_share_the_job_task_child_table(self):
		root = Path(__file__).resolve().parents[1] / "warehousing" / "doctype"
		found = {}
		for path in root.glob("*/*.json"):
			data = json.loads(path.read_text())
			if data.get("doctype") != "DocType":
				continue
			if data.get("name") in WAREHOUSING_JOB_TASK_PARENTS:
				found[data["name"]] = data
		self.assertEqual(set(found), set(WAREHOUSING_JOB_TASK_PARENTS))
		for name, data in found.items():
			job_tasks = [field for field in data["fields"] if field.get("fieldname") == "job_tasks"]
			self.assertEqual(len(job_tasks), 1, name)
			self.assertEqual(job_tasks[0].get("fieldtype"), "Table", name)
			self.assertEqual(job_tasks[0].get("options"), "Job Task", name)

	def test_repair_patch_uses_the_doctype_name_and_is_run_again(self):
		patches = Path(__file__).resolve().parents[1] / "patches"
		original = (patches / "v3_0_add_job_task_child_columns.py").read_text()
		rerun = (patches / "v3_0_repair_job_task_parent_columns.py").read_text()
		self.assertIn("table_exists_argument()", original)
		self.assertNotIn("table_exists(TABLE", original)
		self.assertNotIn('table_exists("tabJob Task"', original)
		self.assertIn("v3_0_add_job_task_child_columns", rerun)
		listed = (patches.parent / "patches.txt").read_text()
		self.assertIn("logistics.patches.v3_0_repair_job_task_parent_columns", listed)
