# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Unit tests for automatic WIP / Accrual recognition."""

from __future__ import unicode_literals

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from frappe.utils import add_days, nowdate

from logistics.job_management.auto_recognition import (
	auto_recognize_job,
	enqueue_auto_recognize,
	process_auto_recognition,
)
from logistics.job_management.recognition_engine import get_recognition_settings


def _job(**kwargs):
	data = {
		"doctype": "Air Shipment",
		"name": "AS-TEST-1",
		"docstatus": 1,
		"company": "Test Co",
		"status": "In Progress",
		"job_status": "In Progress",
		"wip_closed": 0,
		"accrual_closed": 0,
	}
	data.update(kwargs)
	job = SimpleNamespace(**data)
	job.get = lambda key, default=None: getattr(job, key, default)
	job.reload = MagicMock()
	return job


class TestEnqueueAutoRecognize(unittest.TestCase):
	def tearDown(self):
		import frappe

		frappe.flags.in_auto_recognition = False

	@patch("logistics.job_management.auto_recognition.frappe.enqueue")
	@patch("logistics.job_management.auto_recognition.company_auto_recognize_enabled", return_value=True)
	def test_enqueues_submitted_job(self, _enabled, enqueue):
		import frappe

		frappe.flags.in_auto_recognition = False
		enqueue_auto_recognize(_job())
		enqueue.assert_called_once()
		kwargs = enqueue.call_args[1]
		self.assertEqual(
			kwargs["job_id"],
			"auto_recognize|Air Shipment|AS-TEST-1",
		)
		self.assertTrue(kwargs["deduplicate"])
		self.assertTrue(kwargs["enqueue_after_commit"])

	@patch("logistics.job_management.auto_recognition.frappe.enqueue")
	@patch("logistics.job_management.auto_recognition.company_auto_recognize_enabled", return_value=True)
	def test_skips_draft(self, _enabled, enqueue):
		enqueue_auto_recognize(_job(docstatus=0))
		enqueue.assert_not_called()

	@patch("logistics.job_management.auto_recognition.frappe.enqueue")
	@patch("logistics.job_management.auto_recognition.company_auto_recognize_enabled", return_value=False)
	def test_skips_when_policy_off(self, _enabled, enqueue):
		enqueue_auto_recognize(_job())
		enqueue.assert_not_called()

	@patch("logistics.job_management.auto_recognition.frappe.enqueue")
	@patch("logistics.job_management.auto_recognition.company_auto_recognize_enabled", return_value=True)
	def test_skips_when_already_in_auto_recognition(self, _enabled, enqueue):
		import frappe

		frappe.flags.in_auto_recognition = True
		enqueue_auto_recognize(_job())
		enqueue.assert_not_called()


class TestAutoRecognizeJob(unittest.TestCase):
	def tearDown(self):
		import frappe

		frappe.flags.in_auto_recognition = False

	def _patch_ready(self, job, settings=None, rec_date="today"):
		settings = settings or {
			"auto_recognize": True,
			"enable_wip_recognition": True,
			"enable_accrual_recognition": True,
		}
		if rec_date == "today":
			rec_date = nowdate()
		engine = MagicMock()
		engine.get_recognition_date.return_value = rec_date
		engine.has_pending_wip_recognition.return_value = True
		engine.has_pending_accrual_recognition.return_value = True
		p_exists = patch(
			"logistics.job_management.auto_recognition.frappe.db.exists",
			return_value=True,
		)
		p_get = patch(
			"logistics.job_management.auto_recognition.frappe.get_doc",
			return_value=job,
		)
		p_settings = patch(
			"logistics.job_management.auto_recognition.get_recognition_settings",
			return_value=settings,
		)
		p_engine = patch(
			"logistics.job_management.auto_recognition.RecognitionEngine",
			return_value=engine,
		)
		p_sync = patch(
			"logistics.job_management.auto_recognition.sync_job_recognition_fields_from_policy",
		)
		return p_exists, p_get, p_settings, p_engine, p_sync, engine

	def test_skips_when_auto_recognize_off(self):
		job = _job()
		p_exists, p_get, p_settings, p_engine, p_sync, engine = self._patch_ready(
			job,
			settings={
				"auto_recognize": False,
				"enable_wip_recognition": True,
				"enable_accrual_recognition": True,
			},
		)
		with p_exists, p_get, p_settings, p_engine, p_sync:
			auto_recognize_job("Air Shipment", "AS-TEST-1")
		engine.recognize_wip.assert_not_called()
		engine.recognize_accruals.assert_not_called()

	def test_skips_when_recognition_date_missing(self):
		job = _job()
		p_exists, p_get, p_settings, p_engine, p_sync, engine = self._patch_ready(
			job, rec_date=None
		)
		with p_exists, p_get, p_settings, p_engine, p_sync:
			auto_recognize_job("Air Shipment", "AS-TEST-1")
		engine.recognize_wip.assert_not_called()
		engine.recognize_accruals.assert_not_called()

	def test_skips_future_recognition_date(self):
		job = _job()
		p_exists, p_get, p_settings, p_engine, p_sync, engine = self._patch_ready(
			job, rec_date=add_days(nowdate(), 3)
		)
		with p_exists, p_get, p_settings, p_engine, p_sync:
			auto_recognize_job("Air Shipment", "AS-TEST-1")
		engine.recognize_wip.assert_not_called()
		engine.recognize_accruals.assert_not_called()

	def test_skips_closed_job(self):
		job = _job(job_status="Closed", status="Closed")
		p_exists, p_get, p_settings, p_engine, p_sync, engine = self._patch_ready(job)
		with p_exists, p_get, p_settings, p_engine, p_sync:
			auto_recognize_job("Air Shipment", "AS-TEST-1")
		engine.recognize_wip.assert_not_called()

	def test_posts_when_date_is_ready(self):
		job = _job()
		p_exists, p_get, p_settings, p_engine, p_sync, engine = self._patch_ready(job)
		with p_exists, p_get, p_settings, p_engine, p_sync:
			auto_recognize_job("Air Shipment", "AS-TEST-1")
		engine.recognize_wip.assert_called_once()
		engine.recognize_accruals.assert_called_once()
		job.reload.assert_called()


class TestProcessAutoRecognition(unittest.TestCase):
	@patch("logistics.job_management.auto_recognition.enqueue_auto_recognize")
	@patch("logistics.job_management.auto_recognition._pending_job_names")
	@patch(
		"logistics.job_management.auto_recognition.frappe.get_all",
		return_value=["Test Co"],
	)
	def test_enqueues_pending_jobs_for_auto_companies(self, _get_all, pending, enqueue):
		pending.side_effect = lambda job_type, company: (
			["AS-1"] if job_type == "Air Shipment" else []
		)
		process_auto_recognition()
		enqueue.assert_called_once()
		doc = enqueue.call_args[0][0]
		self.assertEqual(doc.doctype, "Air Shipment")
		self.assertEqual(doc.name, "AS-1")
		self.assertEqual(doc.company, "Test Co")


class TestGetRecognitionSettingsAutoRecognize(unittest.TestCase):
	def test_auto_recognize_comes_from_enabled_policy(self):
		import frappe

		job = _job()
		policy = frappe._dict(
			enabled=1,
			enable_wip_recognition=1,
			enable_accrual_recognition=1,
			auto_recognize=1,
			minimum_wip_amount=0,
			minimum_accrual_amount=0,
			name="RRPS-00001",
		)
		row = frappe._dict(
			recognition_date_basis="Job Booking Date",
			wip_account="WIP",
			revenue_liability_account="RL",
			cost_accrual_account="CA",
			accrued_cost_liability_account="ACL",
		)
		with patch(
			"logistics.job_management.recognition_engine.resolve_policy_row_for_job",
			return_value=(policy, row),
		):
			settings = get_recognition_settings(job)
		self.assertTrue(settings["auto_recognize"])

	def test_unsynced_job_checkboxes_do_not_disable_policy(self):
		"""Check fields default to 0; that must not override an enabled policy."""
		import frappe

		job = _job(wip_recognition_enabled=0, accrual_recognition_enabled=0)
		policy = frappe._dict(
			enabled=1,
			enable_wip_recognition=1,
			enable_accrual_recognition=1,
			auto_recognize=1,
			minimum_wip_amount=0,
			minimum_accrual_amount=0,
			name="RRPS-00001",
		)
		row = frappe._dict(
			recognition_date_basis="Job Booking Date",
			wip_account="WIP",
			revenue_liability_account="RL",
			cost_accrual_account="CA",
			accrued_cost_liability_account="ACL",
		)
		with patch(
			"logistics.job_management.recognition_engine.resolve_policy_row_for_job",
			return_value=(policy, row),
		):
			settings = get_recognition_settings(job)
		self.assertTrue(settings["enable_wip_recognition"])
		self.assertTrue(settings["enable_accrual_recognition"])
		self.assertTrue(settings["auto_recognize"])

	def test_auto_recognize_false_when_no_policy(self):
		job = _job()
		with patch(
			"logistics.job_management.recognition_engine.resolve_policy_row_for_job",
			return_value=(None, None),
		):
			settings = get_recognition_settings(job)
		self.assertFalse(settings["auto_recognize"])
