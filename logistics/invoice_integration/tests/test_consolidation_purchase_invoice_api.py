# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import unittest
from unittest.mock import patch

import frappe
from frappe.exceptions import ValidationError

from logistics.invoice_integration.purchase_invoice_api import (
	_PLANNING_SUBMITTED_FOR_PI_MSG,
	_require_consolidation_planning_submitted,
	get_eligible_charges_for_consolidation_purchase_invoice,
)


class TestConsolidationPurchaseInvoicePlanningGuard(unittest.TestCase):
	def test_require_planning_submitted_sea_draft_raises(self):
		doc = frappe._dict(doctype="Sea Consolidation", sea_planning_status="Draft")
		with self.assertRaises(ValidationError) as ctx:
			_require_consolidation_planning_submitted(doc)
		self.assertIn(_PLANNING_SUBMITTED_FOR_PI_MSG, str(ctx.exception))

	def test_require_planning_submitted_air_draft_raises(self):
		doc = frappe._dict(doctype="Air Consolidation", air_planning_status="Draft")
		with self.assertRaises(ValidationError):
			_require_consolidation_planning_submitted(doc)

	def test_require_planning_submitted_defaults_to_draft(self):
		doc = frappe._dict(doctype="Sea Consolidation")
		with self.assertRaises(ValidationError):
			_require_consolidation_planning_submitted(doc)

	def test_require_planning_submitted_sea_submitted_passes(self):
		doc = frappe._dict(doctype="Sea Consolidation", sea_planning_status="Submitted")
		_require_consolidation_planning_submitted(doc)

	def test_require_planning_submitted_air_submitted_passes(self):
		doc = frappe._dict(doctype="Air Consolidation", air_planning_status="Submitted")
		_require_consolidation_planning_submitted(doc)

	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.get_doc")
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.db.exists", return_value=True)
	def test_get_eligible_charges_draft_raises(self, _mock_exists, mock_get_doc):
		mock_get_doc.return_value = frappe._dict(
			doctype="Sea Consolidation",
			name="SC-TEST",
			sea_planning_status="Draft",
			company="Test Company",
		)
		with self.assertRaises(ValidationError) as ctx:
			get_eligible_charges_for_consolidation_purchase_invoice(
				"Sea Consolidation", "SC-TEST"
			)
		self.assertIn(_PLANNING_SUBMITTED_FOR_PI_MSG, str(ctx.exception))
		mock_get_doc.assert_called_once()

	@patch("logistics.invoice_integration.purchase_invoice_api._get_eligible_consolidation_cost_rows", return_value=[])
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.get_doc")
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.db.exists", return_value=True)
	def test_get_eligible_charges_submitted_passes_planning_check(
		self, _mock_exists, mock_get_doc, _mock_cost_rows
	):
		mock_get_doc.return_value = frappe._dict(
			doctype="Sea Consolidation",
			name="SC-TEST",
			sea_planning_status="Submitted",
			company="Test Company",
		)
		result = get_eligible_charges_for_consolidation_purchase_invoice(
			"Sea Consolidation", "SC-TEST"
		)
		self.assertEqual(result["eligible_charges"], [])
		self.assertEqual(result["company"], "Test Company")
