# Copyright (c) 2026, AgilaSoft and contributors
# See license.txt

"""Post → WIP and Accrual does not require Journal Entry create."""

import os
import unittest
from unittest.mock import patch

import frappe

from logistics.job_management.recognition_engine import (
	RecognitionEngine,
	adjust_wip,
	recognize,
)


def _job():
	job = frappe._dict(doctype="Air Shipment", name="AS-1", company="Test Co")
	return job


class TestRecognizeIgnoresJournalEntryPermission(unittest.TestCase):
	def setUp(self):
		self._prev_auto = getattr(frappe.flags, "in_auto_recognition", False)
		self._prev_ignore = getattr(frappe.flags, "ignore_recognition_je_permissions", False)
		frappe.flags.in_auto_recognition = False
		frappe.flags.ignore_recognition_je_permissions = False

	def tearDown(self):
		frappe.flags.in_auto_recognition = self._prev_auto
		frappe.flags.ignore_recognition_je_permissions = self._prev_ignore

	def test_ignore_flag_posts_journal_without_permission(self):
		engine = RecognitionEngine(_job())
		self.assertFalse(engine._ignore_permissions())

		class Journal:
			def __init__(self):
				self.flags = frappe._dict()
				self.inserted_with = None
				self.submitted_with = None

			def insert(self, ignore_permissions=False):
				self.inserted_with = ignore_permissions
				# Simulate a framework reset after insert.
				self.flags.ignore_permissions = False

			def submit(self):
				self.submitted_with = bool(self.flags.ignore_permissions)

		je = Journal()
		engine._insert_and_submit_je(je)
		self.assertFalse(je.inserted_with)
		self.assertFalse(je.submitted_with)

		frappe.flags.ignore_recognition_je_permissions = True
		je = Journal()
		engine._insert_and_submit_je(je)
		self.assertTrue(je.inserted_with)
		self.assertTrue(je.submitted_with)

		saved = {}

		def save(ignore_permissions=False):
			saved["ignore"] = ignore_permissions

		job = _job()
		job.flags = frappe._dict()
		job.save = save
		RecognitionEngine(job)._save_job()
		self.assertTrue(saved["ignore"])
		self.assertTrue(job.flags.ignore_job_change_lock)

	def test_recognize_requires_job_write_and_ignores_journal_entry(self):
		job = _job()
		calls = []
		seen = {}

		def fake_assert(doctype, ptype="read", doc=None):
			calls.append((doctype, ptype))

		class Engine:
			def __init__(self, doc):
				seen["during"] = bool(
					getattr(frappe.flags, "ignore_recognition_je_permissions", False)
				)

			def recognize_wip(self, recognition_date=None):
				return "JE-WIP"

			def recognize_accruals(self, recognition_date=None):
				return "JE-ACC"

		with patch(
			"logistics.job_management.recognition_engine.frappe.get_doc",
			return_value=job,
		), patch(
			"logistics.job_management.recognition_engine.RecognitionEngine",
			Engine,
		), patch(
			"logistics.utils.menu_permission.assert_perm",
			fake_assert,
		):
			result = recognize("Air Shipment", "AS-1")

		self.assertEqual(calls, [("Air Shipment", "write")])
		self.assertNotIn(("Journal Entry", "create"), calls)
		self.assertTrue(seen["during"])
		self.assertFalse(bool(getattr(frappe.flags, "ignore_recognition_je_permissions", False)))
		self.assertEqual(result["wip_journal_entry"], "JE-WIP")
		self.assertEqual(result["accrual_journal_entry"], "JE-ACC")

	def test_recognize_denied_without_job_write(self):
		job = _job()

		def deny(doctype, ptype="read", doc=None):
			raise frappe.PermissionError("Not permitted")

		with patch(
			"logistics.job_management.recognition_engine.frappe.get_doc",
			return_value=job,
		), patch(
			"logistics.job_management.recognition_engine.RecognitionEngine",
		) as engine_cls, patch(
			"logistics.utils.menu_permission.assert_perm",
			deny,
		):
			with self.assertRaises(frappe.PermissionError):
				recognize("Air Shipment", "AS-1")
			engine_cls.assert_not_called()

		self.assertFalse(bool(getattr(frappe.flags, "ignore_recognition_je_permissions", False)))

	def test_recognize_restores_ignore_flag_after_error(self):
		job = _job()
		frappe.flags.ignore_recognition_je_permissions = True

		class Engine:
			def __init__(self, doc):
				pass

			def recognize_wip(self, recognition_date=None):
				raise RuntimeError("post failed")

		with patch(
			"logistics.job_management.recognition_engine.frappe.get_doc",
			return_value=job,
		), patch(
			"logistics.job_management.recognition_engine.RecognitionEngine",
			Engine,
		), patch(
			"logistics.utils.menu_permission.assert_perm",
		):
			with self.assertRaises(RuntimeError):
				recognize("Air Shipment", "AS-1")

		self.assertTrue(bool(getattr(frappe.flags, "ignore_recognition_je_permissions", False)))

	def test_adjust_wip_still_requires_journal_entry_create(self):
		job = _job()
		calls = []

		def fake_assert(doctype, ptype="read", doc=None):
			calls.append((doctype, ptype))

		class Engine:
			def __init__(self, doc):
				pass

			def adjust_wip(self, amount, adjustment_date=None):
				return "JE-ADJ"

		with patch(
			"logistics.job_management.recognition_engine.frappe.get_doc",
			return_value=job,
		), patch(
			"logistics.job_management.recognition_engine.RecognitionEngine",
			Engine,
		), patch(
			"logistics.utils.menu_permission.assert_perm",
			fake_assert,
		):
			name = adjust_wip("Air Shipment", "AS-1", 10)

		self.assertEqual(name, "JE-ADJ")
		self.assertIn(("Air Shipment", "write"), calls)
		self.assertIn(("Journal Entry", "create"), calls)
		self.assertFalse(bool(getattr(frappe.flags, "ignore_recognition_je_permissions", False)))


class TestPostWipMenuDoesNotRequireJournalEntry(unittest.TestCase):
	def _read(self, *parts):
		root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
		with open(os.path.join(root, *parts), encoding="utf-8") as handle:
			return handle.read()

	def test_inferred_gl_gate_skips_wip_and_accrual(self):
		text = self._read("public", "js", "menu_permission.js")
		chunk = text[text.index("function _is_gl_post_label") : text.index("logistics.menu.infer")]
		self.assertNotIn('__("WIP and Accrual")', chunk)
		self.assertIn("Adjust WIP", chunk)
		self.assertIn("Adjust Accruals", chunk)
		self.assertIn("Close Recognition", chunk)

	def test_explicit_post_buttons_omit_journal_entry_create(self):
		for parts in (
			("job_management", "recognition_client.js"),
			("transport", "doctype", "transport_job", "transport_job.js"),
		):
			src = self._read(*parts)
			post = src.split("label: __('Adjust WIP')", 1)[0]
			button = post.split("label: __('WIP and Accrual')", 1)[1]
			self.assertNotIn(
				"Journal Entry",
				button,
				"{0} Post > WIP and Accrual must not require Journal Entry create".format(
					os.path.join(*parts)
				),
			)
