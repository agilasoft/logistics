# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors

import json
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import UnitTestCase
from frappe.utils import flt

from logistics.invoice_integration.billing_currency import convert_amount_to_billing_currency
from logistics.invoice_integration.purchase_invoice_api import create_purchase_invoice


class TestPurchaseInvoiceBillingCurrency(UnitTestCase):
	def _mock_job(self):
		charge = frappe._dict(
			name="ch-1",
			item_code="FREIGHT",
			estimated_cost=500,
			actual_cost=0,
			cost_currency="USD",
			currency="USD",
			purchase_invoice_status=None,
			purchase_invoice=None,
			pay_to="SUPP-1",
		)
		return frappe._dict(
			doctype="Transport Job",
			name="TJ-TEST",
			company="Test Company",
			customer="CUST-1",
			job_number="TJ-TEST",
			charges=[charge],
		)

	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.db.commit")
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.db.set_value")
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.db.table_exists", return_value=True)
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.get_meta")
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.new_doc")
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.get_doc")
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.db.exists", return_value=True)
	@patch(
		"logistics.invoice_integration.purchase_invoice_api._purchase_invoice_naming_context",
		return_value={
			"autoname": "naming_series:",
			"needs_purchase_invoice_name": False,
			"naming_series_options": [],
			"default_naming_series": None,
			"show_naming_series": False,
		},
	)
	@patch(
		"logistics.invoice_integration.purchase_invoice_api.invoice_billing_context",
		return_value={"company_currency": "PHP", "billing_currency": "USD", "billing_exchange_rate": 61.306},
	)
	@patch("logistics.invoice_integration.purchase_invoice_api.charge_to_company_rate_buying", return_value=61.306)
	def test_usd_billing_keeps_usd_cost(
		self,
		_mock_chr,
		_mock_bctx,
		_mock_naming,
		_mock_exists,
		mock_get_doc,
		mock_new_doc,
		mock_get_meta,
		_mock_tbl,
		_mock_sv,
		_mock_commit,
	):
		job = self._mock_job()
		mock_get_doc.return_value = job

		pi = MagicMock()
		pi.items = []
		pi.remarks = ""
		pi.append = lambda field, row: pi.items.append(frappe._dict(row))
		mock_new_doc.return_value = pi

		meta = MagicMock()
		meta.get_field.return_value = None
		mock_get_meta.return_value = meta

		result = create_purchase_invoice(
			job_type="Transport Job",
			job_name="TJ-TEST",
			supplier="SUPP-1",
			posting_date="2026-06-29",
			billing_currency="USD",
			exchange_rate=61.306,
			selected_charge_indices=json.dumps([0]),
		)

		self.assertTrue(result["ok"])
		self.assertEqual(pi.currency, "USD")
		self.assertEqual(pi.conversion_rate, 61.306)
		self.assertEqual(pi.ignore_pricing_rule, 1)
		self.assertEqual(pi.items[0].rate, 500)

	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.db.commit")
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.db.set_value")
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.db.table_exists", return_value=True)
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.get_meta")
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.new_doc")
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.get_doc")
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.db.exists", return_value=True)
	@patch(
		"logistics.invoice_integration.purchase_invoice_api._purchase_invoice_naming_context",
		return_value={
			"autoname": "naming_series:",
			"needs_purchase_invoice_name": False,
			"naming_series_options": [],
			"default_naming_series": None,
			"show_naming_series": False,
		},
	)
	@patch(
		"logistics.invoice_integration.purchase_invoice_api.invoice_billing_context",
		return_value={"company_currency": "PHP", "billing_currency": "PHP", "billing_exchange_rate": 1.0},
	)
	@patch("logistics.invoice_integration.purchase_invoice_api.charge_to_company_rate_buying", return_value=61.306)
	def test_php_billing_converts_usd_cost(
		self,
		_mock_chr,
		_mock_bctx,
		_mock_naming,
		_mock_exists,
		mock_get_doc,
		mock_new_doc,
		mock_get_meta,
		_mock_tbl,
		_mock_sv,
		_mock_commit,
	):
		job = self._mock_job()
		mock_get_doc.return_value = job

		pi = MagicMock()
		pi.items = []
		pi.remarks = ""
		pi.append = lambda field, row: pi.items.append(frappe._dict(row))
		mock_new_doc.return_value = pi

		meta = MagicMock()
		meta.get_field.return_value = None
		mock_get_meta.return_value = meta

		create_purchase_invoice(
			job_type="Transport Job",
			job_name="TJ-TEST",
			supplier="SUPP-1",
			posting_date="2026-06-29",
			billing_currency="PHP",
			exchange_rate=1,
			selected_charge_indices=json.dumps([0]),
		)

		self.assertEqual(pi.currency, "PHP")
		self.assertAlmostEqual(pi.items[0].rate, flt(500 * 61.306), places=2)


class TestPurchaseInvoiceConvertAmount(UnitTestCase):
	def test_usd_cost_to_php_billing(self):
		self.assertAlmostEqual(
			convert_amount_to_billing_currency(500, "USD", "PHP", "PHP", 1, 61.306),
			flt(500 * 61.306),
			places=2,
		)


class TestMiceProjectPurchaseInvoiceHook(UnitTestCase):
	@patch("logistics.invoice_integration.purchase_invoice_api.push_consolidation_charges_to_dockets")
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.db.commit")
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.db.set_value")
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.db.table_exists", return_value=True)
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.get_meta")
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.new_doc")
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.get_doc")
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.db.exists", return_value=True)
	@patch(
		"logistics.invoice_integration.purchase_invoice_api._purchase_invoice_naming_context",
		return_value={
			"autoname": "naming_series:",
			"needs_purchase_invoice_name": False,
			"naming_series_options": [],
			"default_naming_series": None,
			"show_naming_series": False,
		},
	)
	@patch(
		"logistics.invoice_integration.purchase_invoice_api.invoice_billing_context",
		return_value={"company_currency": "PHP", "billing_currency": "PHP", "billing_exchange_rate": 1.0},
	)
	@patch("logistics.invoice_integration.purchase_invoice_api.charge_to_company_rate_buying", return_value=1.0)
	def test_create_purchase_invoice_pushes_allocated_mice_charges(
		self,
		_mock_chr,
		_mock_bctx,
		_mock_naming,
		_mock_exists,
		mock_get_doc,
		mock_new_doc,
		mock_get_meta,
		_mock_tbl,
		_mock_sv,
		_mock_commit,
		mock_push,
	):
		charge = frappe._dict(
			name="cass-1",
			item_code="DOCFEE",
			total_amount=10,
			unit_rate=10,
			quantity=1,
			currency="PHP",
			pay_to="SUPP-1",
			purchase_invoice_status=None,
			purchase_invoice=None,
		)
		job = frappe._dict(
			doctype="MICE Project",
			name="PROJ-TEST",
			company="Test Company",
			job_number="PROJ-TEST",
			consolidation_charges=[charge],
		)
		mock_get_doc.return_value = job

		pi = MagicMock()
		pi.name = "PINV-0001"
		pi.items = []
		pi.remarks = ""
		pi.append = lambda field, row: pi.items.append(frappe._dict(row))
		mock_new_doc.return_value = pi

		meta = MagicMock()
		meta.get_field.return_value = None
		mock_get_meta.return_value = meta

		create_purchase_invoice(
			job_type="MICE Project",
			job_name="PROJ-TEST",
			supplier="SUPP-1",
			posting_date="2026-06-29",
			billing_currency="PHP",
			exchange_rate=1,
			selected_charge_indices=json.dumps([0]),
		)

		mock_push.assert_called_once()
		args, kwargs = mock_push.call_args
		self.assertEqual(args[0], job)
		self.assertEqual(kwargs["selected_charges"], [charge])
		self.assertEqual(kwargs["purchase_invoice"], "PINV-0001")
