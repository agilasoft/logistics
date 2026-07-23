# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Unit tests for two-tier job readiness (charges, documents, milestones, settings)."""

from __future__ import unicode_literals

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from logistics.job_management import job_readiness


def _charge(**kwargs):
	defaults = {
		"item_code": "FRT",
		"item_name": "Freight",
		"estimated_revenue": 0,
		"actual_revenue": 0,
		"estimated_cost": 0,
		"actual_cost": 0,
		"sales_invoice": None,
		"sales_invoice_status": "Not Requested",
		"purchase_invoice": None,
		"purchase_invoice_status": "Not Requested",
		"charge_type": "",
	}
	defaults.update(kwargs)
	return SimpleNamespace(**defaults)


def _doc(doctype="Sea Shipment", **kwargs):
	data = {
		"doctype": doctype,
		"name": "TEST-JOB-001",
		"docstatus": 1,
		"job_status": "Reopened",
		"charges": [],
		"documents": [],
		"milestones": [],
		"flags": frappe._dict(),
	}
	data.update(kwargs)
	doc = SimpleNamespace(**data)
	doc.get = lambda key, default=None: getattr(doc, key, default)
	return doc


class TestJobReadinessCharges(unittest.TestCase):
	@patch("logistics.job_management.job_readiness._invoice_submitted")
	def test_revenue_requires_submitted_si(self, mock_sub):
		mock_sub.return_value = True
		doc = _doc(
			charges=[
				_charge(
					estimated_revenue=100,
					sales_invoice="SI-1",
					sales_invoice_status="Posted",
				)
			]
		)
		self.assertEqual(job_readiness.check_charges_posted(doc), [])

	@patch("logistics.job_management.job_readiness._invoice_submitted")
	def test_draft_si_does_not_count(self, mock_sub):
		mock_sub.return_value = False
		doc = _doc(
			charges=[
				_charge(
					estimated_revenue=100,
					sales_invoice="SI-DRAFT",
					sales_invoice_status="Requested",
				)
			]
		)
		issues = job_readiness.check_charges_posted(doc)
		self.assertEqual(len(issues), 1)
		self.assertEqual(issues[0]["code"], "charge_not_posted_si")

	@patch("logistics.job_management.job_readiness._invoice_submitted")
	def test_posted_status_but_draft_docstatus_fails(self, mock_sub):
		# Inconsistent: status says Posted but invoice not submitted
		mock_sub.return_value = False
		doc = _doc(
			charges=[
				_charge(
					estimated_revenue=100,
					sales_invoice="SI-X",
					sales_invoice_status="Posted",
				)
			]
		)
		issues = job_readiness.check_charges_posted(doc)
		self.assertEqual(len(issues), 1)
		self.assertEqual(issues[0]["code"], "charge_not_posted_si")

	@patch("logistics.job_management.job_readiness._invoice_submitted")
	def test_cost_requires_submitted_pi(self, mock_sub):
		mock_sub.return_value = True
		doc = _doc(
			charges=[
				_charge(
					estimated_cost=50,
					purchase_invoice="PI-1",
					purchase_invoice_status="Paid",
				)
			]
		)
		self.assertEqual(job_readiness.check_charges_posted(doc), [])

	def test_zero_amount_skipped(self):
		doc = _doc(charges=[_charge(estimated_revenue=0, estimated_cost=0)])
		self.assertEqual(job_readiness.check_charges_posted(doc), [])

	def test_no_item_code_skipped(self):
		doc = _doc(
			charges=[_charge(item_code=None, charge_item=None, estimated_revenue=100)]
		)
		self.assertEqual(job_readiness.check_charges_posted(doc), [])

	@patch("logistics.job_management.job_readiness._invoice_submitted")
	def test_both_si_and_pi_required(self, mock_sub):
		mock_sub.return_value = True
		doc = _doc(
			charges=[
				_charge(
					estimated_revenue=100,
					estimated_cost=40,
					sales_invoice="SI-1",
					sales_invoice_status="Posted",
					# PI missing
				)
			]
		)
		issues = job_readiness.check_charges_posted(doc)
		self.assertEqual(len(issues), 1)
		self.assertEqual(issues[0]["code"], "charge_not_posted_pi")


class TestJobReadinessDocumentsAndMilestones(unittest.TestCase):
	@patch("logistics.document_management.api.get_incomplete_required_documents")
	def test_documents_incomplete(self, mock_inc):
		mock_inc.return_value = ["Bill of Lading (Pending)"]
		doc = _doc()
		issues = job_readiness.check_required_documents(doc)
		self.assertEqual(len(issues), 1)
		self.assertEqual(issues[0]["code"], "document_incomplete")

	def test_milestones_incomplete(self):
		doc = _doc(
			milestones=[
				{"milestone": "ATD", "status": "Completed"},
				{"milestone": "ATA", "status": "Planned"},
			]
		)
		issues = job_readiness.check_milestones_complete(doc)
		self.assertEqual(len(issues), 1)
		self.assertIn("ATA", issues[0]["message"])

	def test_milestones_all_complete(self):
		doc = _doc(
			milestones=[
				{"milestone": "ATD", "status": "Completed"},
				{"milestone": "ATA", "status": "Completed"},
			]
		)
		self.assertEqual(job_readiness.check_milestones_complete(doc), [])


class TestJobReadinessSettings(unittest.TestCase):
	@patch("logistics.job_management.job_readiness.check_charges_posted")
	@patch("logistics.job_management.job_readiness.check_milestones_complete")
	@patch("logistics.job_management.job_readiness.check_required_documents")
	@patch("logistics.job_management.job_readiness._settings")
	def test_close_defaults_block_all_three(self, mock_settings, mock_docs, mock_ms, mock_ch):
		mock_settings.return_value = SimpleNamespace(
			block_close_if_required_documents_pending=1,
			block_close_if_milestones_incomplete=1,
			block_close_if_charges_not_posted=1,
			block_complete_if_required_documents_pending=0,
			block_complete_if_milestones_incomplete=0,
			block_complete_if_charges_not_posted=0,
		)
		mock_docs.return_value = [job_readiness._issue("document_incomplete", "doc")]
		mock_ms.return_value = [job_readiness._issue("milestone_incomplete", "ms")]
		mock_ch.return_value = [job_readiness._issue("charge_not_posted_si", "ch")]
		doc = _doc()
		blocking = job_readiness._blocking_issues_for_gate(doc, "close")
		self.assertEqual(len(blocking), 3)

	@patch("logistics.job_management.job_readiness.check_charges_posted")
	@patch("logistics.job_management.job_readiness.check_milestones_complete")
	@patch("logistics.job_management.job_readiness.check_required_documents")
	@patch("logistics.job_management.job_readiness._settings")
	def test_complete_defaults_do_not_block(self, mock_settings, mock_docs, mock_ms, mock_ch):
		mock_settings.return_value = SimpleNamespace(
			block_close_if_required_documents_pending=1,
			block_close_if_milestones_incomplete=1,
			block_close_if_charges_not_posted=1,
			block_complete_if_required_documents_pending=0,
			block_complete_if_milestones_incomplete=0,
			block_complete_if_charges_not_posted=0,
		)
		mock_docs.return_value = [job_readiness._issue("document_incomplete", "doc")]
		mock_ms.return_value = [job_readiness._issue("milestone_incomplete", "ms")]
		mock_ch.return_value = [job_readiness._issue("charge_not_posted_si", "ch")]
		doc = _doc(job_status="In Progress")
		blocking = job_readiness._blocking_issues_for_gate(doc, "complete")
		self.assertEqual(blocking, [])
		# helpers should not be called when settings off
		mock_docs.assert_not_called()
		mock_ms.assert_not_called()
		mock_ch.assert_not_called()

	@patch("logistics.job_management.job_readiness._blocking_issues_for_gate")
	def test_enforce_throws(self, mock_block):
		mock_block.return_value = [
			job_readiness._issue("charge_not_posted_si", "Charge #1 not posted")
		]
		doc = _doc()
		with self.assertRaises(frappe.ValidationError):
			job_readiness.enforce_job_readiness(doc, gate="close")


class TestJobReadinessOpsWarning(unittest.TestCase):
	def test_sea_ops_terminal_warning(self):
		doc = _doc(shipping_status="In Transit")
		issues = job_readiness.check_ops_terminal_status(doc)
		self.assertEqual(len(issues), 1)
		self.assertEqual(issues[0]["severity"], "warning")
		self.assertEqual(issues[0]["code"], "ops_not_terminal")

	def test_sea_delivered_ok(self):
		doc = _doc(shipping_status="Delivered")
		self.assertEqual(job_readiness.check_ops_terminal_status(doc), [])


class TestGetJobReadiness(unittest.TestCase):
	@patch("logistics.job_management.job_readiness.check_ops_terminal_status", return_value=[])
	@patch("logistics.job_management.job_readiness.check_charges_posted", return_value=[])
	@patch("logistics.job_management.job_readiness.check_milestones_complete", return_value=[])
	@patch("logistics.job_management.job_readiness.check_required_documents", return_value=[])
	def test_close_ok(self, *mocks):
		doc = _doc()
		result = job_readiness.get_job_readiness(doc, gate="close")
		self.assertTrue(result["ok"])
		self.assertEqual(result["gate"], "close")
		self.assertEqual(result["errors"], [])

	@patch("logistics.document_management.api.get_incomplete_required_documents")
	def test_submit_master_data(self, mock_docs):
		mock_docs.return_value = []
		doc = _doc(
			doctype="Air Shipment",
			booking_date=None,
			air_booking=None,
			shipper=None,
			consignee="C",
			origin_port="AAA",
			destination_port="BBB",
			direction="Export",
			local_customer="CUST",
			airline=None,
		)
		result = job_readiness.get_job_readiness(doc, gate="submit")
		codes = {e["code"] for e in result["errors"]}
		self.assertIn("missing_party", codes)
		warn_codes = {w["code"] for w in result["warnings"]}
		self.assertIn("missing_carrier", warn_codes)


class TestIncompleteDocumentsHelper(unittest.TestCase):
	def test_get_incomplete_required_documents(self):
		from logistics.document_management.api import get_incomplete_required_documents

		doc = _doc(
			documents=[
				{"is_required": 1, "document_type": "BL", "status": "Pending"},
				{"is_required": 1, "document_type": "CI", "status": "Received"},
				{"is_required": 0, "document_type": "POD", "status": "Pending"},
			]
		)
		# row.get for SimpleNamespace — documents need dict-like get
		# rebuild with frappe._dict rows
		doc.documents = [
			frappe._dict({"is_required": 1, "document_type": "BL", "status": "Pending"}),
			frappe._dict({"is_required": 1, "document_type": "CI", "status": "Received"}),
			frappe._dict({"is_required": 0, "document_type": "POD", "status": "Pending"}),
		]
		incomplete = get_incomplete_required_documents(doc)
		self.assertEqual(len(incomplete), 1)
		self.assertIn("BL", incomplete[0])
