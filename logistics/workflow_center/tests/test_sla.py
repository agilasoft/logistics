# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Workflow Center SLA reads must not require columns that migrate has not added yet."""

from __future__ import annotations

import unittest
from pathlib import Path

from logistics.workflow_center.sla import (
	SLA_COLUMNS,
	WORKFLOW_STATE_SLA_FIELDS,
	is_unknown_column_error,
	load_sla_config,
	sla_columns_ready,
	sla_config_from_row,
)


ROOT = Path(__file__).resolve().parents[3]


def _load_sla_module(path: Path) -> dict:
	namespace: dict = {}
	exec(path.read_text(), namespace)
	return namespace


class _UnknownColumn(Exception):
	def __init__(self):
		super().__init__(1054, "Unknown column 'wc_sla_enabled' in 'SELECT'")


class TestWorkflowStateSla(unittest.TestCase):
	def test_missing_column_skips_the_query(self):
		def has_column(doctype, column):
			return column != "wc_sla_enabled"

		def get_value(*args, **kwargs):
			raise AssertionError("dashboard must not select SLA columns that are not migrated")

		self.assertFalse(sla_columns_ready(has_column))
		self.assertEqual(load_sla_config("Pending", has_column, get_value), {"enabled": False})

	def test_unknown_column_error_disables_sla(self):
		def has_column(doctype, column):
			return True

		def get_value(*args, **kwargs):
			raise _UnknownColumn()

		self.assertEqual(load_sla_config("Pending", has_column, get_value), {"enabled": False})
		self.assertTrue(is_unknown_column_error(_UnknownColumn()))

	def test_other_database_errors_still_raise(self):
		def has_column(doctype, column):
			return True

		def get_value(*args, **kwargs):
			raise RuntimeError("connection lost")

		with self.assertRaises(RuntimeError):
			load_sla_config("Pending", has_column, get_value)

	def test_enabled_state_returns_duration(self):
		seen = {}

		def has_column(doctype, column):
			return True

		def get_value(doctype, name, fields, as_dict=False):
			seen["args"] = (doctype, name, tuple(fields), as_dict)
			return {"wc_sla_enabled": 1, "wc_sla_unit": "Days", "wc_sla_value": "2"}

		config = load_sla_config("Approved", has_column, get_value)
		self.assertEqual(
			seen["args"],
			("Workflow State", "Approved", SLA_COLUMNS, True),
		)
		self.assertEqual(config, {"enabled": True, "unit": "Days", "value": 2.0})

	def test_blank_state_and_disabled_flag(self):
		def has_column(doctype, column):
			return True

		def get_value(*args, **kwargs):
			return {"wc_sla_enabled": 0, "wc_sla_unit": "Hours", "wc_sla_value": 4}

		self.assertEqual(load_sla_config("", has_column, get_value), {"enabled": False})
		self.assertEqual(load_sla_config(None, has_column, get_value), {"enabled": False})
		self.assertEqual(sla_config_from_row(get_value()), {"enabled": False})
		self.assertEqual(sla_config_from_row(None), {"enabled": False})
		self.assertEqual(
			sla_config_from_row({"wc_sla_enabled": 1, "wc_sla_value": "nope"}),
			{"enabled": True, "unit": "Hours", "value": 0.0},
		)

	def test_migrate_creates_the_columns_the_dashboard_reads(self):
		fieldnames = [field["fieldname"] for field in WORKFLOW_STATE_SLA_FIELDS]
		for column in SLA_COLUMNS:
			self.assertIn(column, fieldnames)
		patches = (ROOT / "logistics/patches.txt").read_text()
		self.assertIn("logistics.patches.v3_0_add_workflow_state_sla_fields", patches)
		patch = (ROOT / "logistics/patches/v3_0_add_workflow_state_sla_fields.py").read_text()
		self.assertIn("WORKFLOW_STATE_SLA_FIELDS", patch)

	def test_standalone_app_reads_the_same_columns(self):
		logistics = _load_sla_module(ROOT / "logistics/workflow_center/sla.py")
		standalone = _load_sla_module(ROOT / "workflow_center/workflow_center/sla.py")
		self.assertEqual(logistics["SLA_COLUMNS"], standalone["SLA_COLUMNS"])
		self.assertEqual(
			[field["fieldname"] for field in logistics["WORKFLOW_STATE_SLA_FIELDS"]],
			[field["fieldname"] for field in standalone["WORKFLOW_STATE_SLA_FIELDS"]],
		)
		self.assertEqual(
			{field["fieldname"] for field in standalone["WORKFLOW_STATE_SLA_FIELDS"] if field["fieldname"] in SLA_COLUMNS},
			set(SLA_COLUMNS),
		)


if __name__ == "__main__":
	unittest.main()
