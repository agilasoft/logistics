# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Job Task child-column repair. No database."""

from __future__ import annotations

import unittest

from logistics.job_management.job_task_child_schema import (
	add_column_clauses,
	missing_child_link_columns,
	relink_statement,
	should_relink_legacy_rows,
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
