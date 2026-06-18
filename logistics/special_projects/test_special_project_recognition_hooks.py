# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

"""Regression tests for Special Project WIP/accrual recognition UI wiring (#978)."""

import unittest
from types import SimpleNamespace

from logistics import hooks
from logistics.job_management.recognition_engine import RecognitionEngine


class _MockSpecialProjectJob:
	"""Minimal job doc stub for RecognitionEngine charge-line checks."""

	def __init__(self, charges, **fields):
		self.doctype = "Special Project"
		self.company = fields.get("company", "Test Company")
		self.charges = charges
		self.estimated_revenue = fields.get("estimated_revenue", 0)
		self.wip_amount = fields.get("wip_amount", 0)
		self.estimated_costs = fields.get("estimated_costs", 0)
		self.accrual_amount = fields.get("accrual_amount", 0)

	def get(self, key, default=None):
		return getattr(self, key, default)


class TestSpecialProjectRecognitionHooks(unittest.TestCase):
	def test_doctype_js_includes_recognition_scripts(self):
		scripts = hooks.doctype_js.get("Special Project") or []
		self.assertIn(
			"job_management/recognition_client.js",
			scripts,
			"Special Project must load recognition_client.js so Post > WIP and Accrual appears",
		)
		self.assertIn(
			"job_management/recognition_policy_fields.js",
			scripts,
			"Special Project must load recognition_policy_fields.js for policy field sync",
		)

	def test_doctype_js_paths_resolve_on_disk(self):
		import os

		import frappe
		from frappe.desk.form.meta import get_code_files_via_hooks

		for path in get_code_files_via_hooks("doctype_js", "Special Project"):
			self.assertTrue(
				os.path.exists(path),
				f"Special Project doctype_js path must exist: {path}",
			)


class TestSpecialProjectRecognitionPending(unittest.TestCase):
	def _engine(self, charges, **header):
		return RecognitionEngine(_MockSpecialProjectJob(charges, **header))

	def test_charges_table_is_charges(self):
		engine = self._engine([])
		self.assertEqual(engine._get_charges_table_name(), "charges")

	def test_pending_wip_when_charge_has_revenue_and_no_je(self):
		charge = SimpleNamespace(
			charge_type="Service",
			estimated_revenue=100,
			wip_recognition_journal_entry=None,
		)
		engine = self._engine([charge])
		self.assertTrue(engine.has_pending_wip_recognition())

	def test_no_pending_wip_when_all_lines_recognized(self):
		charge = SimpleNamespace(
			charge_type="Service",
			estimated_revenue=100,
			wip_recognition_journal_entry="JE-TEST-001",
		)
		engine = self._engine([charge], estimated_revenue=100, wip_amount=100)
		self.assertFalse(engine.has_pending_wip_recognition())

	def test_pending_accrual_when_charge_has_cost_and_no_je(self):
		charge = SimpleNamespace(
			charge_type="Service",
			estimated_cost=50,
			accrual_recognition_journal_entry=None,
		)
		engine = self._engine([charge])
		self.assertTrue(engine.has_pending_accrual_recognition())

	def test_disbursement_charge_excluded_from_pending_wip(self):
		charge = SimpleNamespace(
			charge_type="Disbursement",
			estimated_revenue=100,
			wip_recognition_journal_entry=None,
		)
		engine = self._engine([charge], estimated_revenue=0, wip_amount=0)
		self.assertFalse(engine.has_pending_wip_recognition())
