# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Child-link column repair. No database."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from logistics.child_link_schema import (
	CHILD_LINK_COLUMNS,
	REPAIRS,
	ChildLinkRepair,
	add_column_clauses,
	missing_child_link_columns,
	relink_statement,
	should_relink_legacy_rows,
)

APP = Path(__file__).resolve().parents[1]


def _doctypes():
	found = {}
	for path in APP.rglob("*.json"):
		if "doctype" not in path.parts:
			continue
		try:
			data = json.loads(path.read_text())
		except (OSError, json.JSONDecodeError):
			continue
		if data.get("doctype") != "DocType" or not data.get("name"):
			continue
		found.setdefault(data["name"], []).append(data)
	return found


class TestChildLinkSchema(unittest.TestCase):
	def test_standalone_table_is_missing_the_child_link(self):
		columns = ["name", "factor_name", "idx"]
		self.assertEqual(missing_child_link_columns(columns), list(CHILD_LINK_COLUMNS))
		repair = REPAIRS[0]
		self.assertFalse(should_relink_legacy_rows(repair, columns + list(CHILD_LINK_COLUMNS)))

	def test_fresh_child_table_needs_no_columns(self):
		columns = ["name", *CHILD_LINK_COLUMNS, "idx"]
		self.assertEqual(missing_child_link_columns(columns), [])

	def test_add_column_clauses_name_only_the_child_link(self):
		clauses = add_column_clauses(["parent", "parentfield", "parenttype"], 140)
		self.assertEqual(
			clauses,
			[
				"ADD COLUMN `parent` varchar(140)",
				"ADD COLUMN `parentfield` varchar(140)",
				"ADD COLUMN `parenttype` varchar(140)",
			],
		)
		with self.assertRaises(ValueError):
			add_column_clauses(["rate_name"], 140)
		with self.assertRaises(ValueError):
			add_column_clauses(["parent"], 0)

	def test_table_exists_argument_is_the_doctype_not_the_physical_name(self):
		for repair in REPAIRS:
			self.assertEqual(repair.table_exists_argument(), repair.doctype)
			self.assertEqual("tab" + repair.table_exists_argument(), repair.table)
			self.assertNotEqual("tab" + repair.table, repair.table)
			self.assertFalse(repair.doctype.startswith("tab"))

	def test_repair_does_not_invent_a_legacy_link(self):
		for repair in REPAIRS:
			self.assertEqual(repair.legacy_columns, ())
			columns = ["name", *CHILD_LINK_COLUMNS, "rate_name", "job_no"]
			self.assertFalse(should_relink_legacy_rows(repair, columns))
		sample = ChildLinkRepair(
			"Example",
			legacy_columns=("job_no", "job_type"),
			legacy_parentfield="job_tasks",
		)
		self.assertFalse(should_relink_legacy_rows(sample, ["job_no", "job_type"]))
		self.assertTrue(
			should_relink_legacy_rows(sample, ["job_no", "job_type", *CHILD_LINK_COLUMNS])
		)
		statement = relink_statement(sample)
		self.assertIn("parent = `job_no`", statement)
		self.assertIn("parenttype = `job_type`", statement)
		self.assertIn("parentfield = 'job_tasks'", statement)
		self.assertIn("IFNULL(parent, '') = ''", statement)

	def test_parents_that_load_these_tables_point_at_them(self):
		doctypes = _doctypes()
		for repair in REPAIRS:
			self.assertIn(repair.doctype, doctypes, repair.doctype)
			for parent_name, fieldname in repair.parents:
				matches = []
				for data in doctypes[parent_name]:
					for field in data.get("fields") or []:
						if field.get("fieldname") != fieldname:
							continue
						if field.get("fieldtype") not in ("Table", "Table MultiSelect"):
							continue
						matches.append(field.get("options"))
				self.assertEqual(matches, [repair.doctype], f"{parent_name}.{fieldname}")

	def test_non_istable_grids_without_a_parent_field_are_repaired(self):
		"""A Table field whose target is not istable queries WHERE parent=.

		A target that declares parent, parentfield, and parenttype as fields
		gets those columns from schema sync. Virtual targets have no table.
		"""
		doctypes = _doctypes()
		repaired = {repair.doctype: repair for repair in REPAIRS}
		seen = {}
		for copies in doctypes.values():
			for data in copies:
				if data.get("is_virtual"):
					continue
				for field in data.get("fields") or []:
					if field.get("fieldtype") not in ("Table", "Table MultiSelect"):
						continue
					target_name = field.get("options")
					targets = doctypes.get(target_name) or []
					if not targets or any(item.get("is_virtual") for item in targets):
						continue
					if any(item.get("istable") for item in targets):
						continue
					fieldnames = {
						item.get("fieldname")
						for target in targets
						for item in target.get("fields") or []
					}
					if set(CHILD_LINK_COLUMNS).issubset(fieldnames):
						self.assertNotIn(target_name, repaired)
						continue
					seen.setdefault(target_name, set()).add((data["name"], field["fieldname"]))
		self.assertEqual(set(seen), {
			name for name, repair in repaired.items() if repair.parents
		})
		for name, parents in seen.items():
			self.assertEqual(parents, set(repaired[name].parents))

	def test_converted_child_tables_without_parent_fields_are_repaired(self):
		"""First committed version of the same DocType, not a rename."""
		converted = set()
		for path in APP.rglob("**/doctype/**/*.json"):
			if path.is_symlink():
				continue
			try:
				current = json.loads(path.read_text())
			except (OSError, json.JSONDecodeError):
				continue
			if current.get("doctype") != "DocType" or not current.get("istable"):
				continue
			if current.get("is_virtual"):
				continue
			name = current["name"]
			relative = path.relative_to(APP).as_posix()
			log = subprocess.run(
				["git", "log", "--reverse", "--pretty=%H", "--", relative],
				cwd=APP,
				capture_output=True,
				text=True,
				check=False,
			)
			hashes = [line for line in log.stdout.split() if line]
			if not hashes:
				continue
			blob = subprocess.run(
				["git", "show", f"{hashes[0]}:{relative}"],
				cwd=APP,
				capture_output=True,
				check=False,
			)
			try:
				first = json.loads(blob.stdout)
			except json.JSONDecodeError:
				continue
			if first.get("name") != name or first.get("istable"):
				continue
			first_fields = {field.get("fieldname") for field in first.get("fields") or []}
			if set(CHILD_LINK_COLUMNS).issubset(first_fields):
				continue
			converted.add(name)
		repaired = {repair.doctype for repair in REPAIRS}
		# Job Task is repaired by its own patch.
		self.assertIn("Job Task", converted)
		self.assertNotIn("Job Task", repaired)
		self.assertEqual(converted - {"Job Task"}, repaired - {
			repair.doctype for repair in REPAIRS if repair.parents
		})

	def test_repair_patch_uses_the_doctype_name(self):
		patch = (APP / "logistics" / "patches" / "v3_0_repair_child_parent_columns.py").read_text()
		self.assertIn("table_exists_argument()", patch)
		self.assertIn("cached=False", patch)
		self.assertNotIn('table_exists("tab', patch)
		self.assertNotIn("table_exists(f\"tab", patch)
		self.assertNotIn("table_exists('tab", patch)
		self.assertNotIn('table_exists("tab" +', patch)
		self.assertNotIn("table_exists(repair.table)", patch)
		self.assertNotIn("table_exists(repair.table,", patch)
		listed = (APP / "logistics" / "patches.txt").read_text()
		self.assertIn("logistics.patches.v3_0_repair_child_parent_columns", listed)
		self.assertIn("logistics.patches.v3_0_repair_job_task_parent_columns", listed)
