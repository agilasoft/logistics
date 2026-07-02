# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import json
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import UnitTestCase
from frappe.utils import flt

from logistics.invoice_integration.billing_currency import (
	convert_amount_to_billing_currency as _convert_charge_amount_to_billing_currency,
	invoice_billing_context as _si_billing_context,
	resolve_selling_charge_currency as _resolve_charge_currency,
)
from logistics.invoice_integration.sales_invoice_api import create_sales_invoice_from_job


class TestConvertChargeAmountToBillingCurrency(UnitTestCase):
	def test_same_currency_unchanged(self):
		self.assertEqual(
			_convert_charge_amount_to_billing_currency(500, "USD", "USD", "PHP", 61.306, 61.306),
			500,
		)

	def test_usd_charge_to_php_billing(self):
		# 500 USD * 61.306 PHP/USD
		self.assertAlmostEqual(
			_convert_charge_amount_to_billing_currency(500, "USD", "PHP", "PHP", 1, 61.306),
			flt(500 * 61.306),
			places=2,
		)

	def test_php_charge_to_usd_billing(self):
		# 30653 PHP / 61.306
		self.assertAlmostEqual(
			_convert_charge_amount_to_billing_currency(30653, "PHP", "USD", "PHP", 61.306, 1),
			500,
			places=2,
		)

	def test_foreign_to_foreign_via_company_base(self):
		# 100 EUR * 70 PHP/EUR / 61.306 PHP/USD
		self.assertAlmostEqual(
			_convert_charge_amount_to_billing_currency(100, "EUR", "USD", "PHP", 61.306, 70),
			flt(100 * 70 / 61.306),
			places=2,
		)


class TestSiBillingContext(UnitTestCase):
	@patch("logistics.invoice_integration.billing_currency.company_currency", return_value="PHP")
	def test_company_currency_billing_rate_is_one(self, _mock_cc):
		ctx = _si_billing_context("Test Co", "PHP", None, "2026-06-29")
		self.assertEqual(ctx["billing_currency"], "PHP")
		self.assertEqual(ctx["billing_exchange_rate"], 1.0)

	@patch("logistics.invoice_integration.billing_currency.company_currency", return_value="PHP")
	def test_foreign_billing_uses_passed_rate(self, _mock_cc):
		ctx = _si_billing_context("Test Co", "USD", 61.306, "2026-06-29")
		self.assertEqual(ctx["billing_currency"], "USD")
		self.assertEqual(ctx["billing_exchange_rate"], 61.306)


class TestResolveChargeCurrency(UnitTestCase):
	def test_docket_prefers_selling_currency(self):
		ch = frappe._dict(selling_currency="USD", currency="PHP")
		self.assertEqual(_resolve_charge_currency(ch, "Docket", "Test Co"), "USD")

	def test_falls_back_to_company_currency(self):
		ch = frappe._dict()
		with patch(
			"logistics.invoice_integration.billing_currency.company_currency",
			return_value="PHP",
		):
			self.assertEqual(_resolve_charge_currency(ch, "Transport Job", "Test Co"), "PHP")


class TestCreateSalesInvoiceBillingCurrency(UnitTestCase):
	def _mock_job(self):
		charge = frappe._dict(
			name="ch-1",
			item_code="DELIVERY",
			item_name="DELIVERY",
			quantity=1,
			unit_rate=500,
			estimated_revenue=500,
			currency="USD",
			sales_invoice_status=None,
			sales_invoice=None,
			apply_95_5_rule=0,
		)
		return frappe._dict(
			doctype="Docket",
			name="PQ-TEST",
			company="Test Company",
			customer="CUST-1",
			job_number="PQ-TEST",
			charges=[charge],
		)

	@patch("logistics.invoice_integration.sales_invoice_api.frappe.db.commit")
	@patch("logistics.invoice_integration.sales_invoice_api.frappe.db.set_value")
	@patch("logistics.invoice_integration.sales_invoice_api.frappe.db.table_exists", return_value=True)
	@patch("logistics.invoice_integration.sales_invoice_api.ensure_sales_invoice_name_for_server_insert")
	@patch("logistics.invoice_integration.sales_invoice_api.apply_freight_95_post_missing_values")
	@patch("logistics.invoice_integration.sales_invoice_api.frappe.get_meta")
	@patch("logistics.invoice_integration.sales_invoice_api.frappe.new_doc")
	@patch("logistics.invoice_integration.sales_invoice_api.frappe.get_doc")
	@patch("logistics.invoice_integration.sales_invoice_api.frappe.db.exists", return_value=True)
	@patch("logistics.invoice_integration.sales_invoice_api.charge_to_company_rate_selling", return_value=61.306)
	@patch(
		"logistics.invoice_integration.sales_invoice_api._si_billing_context",
		return_value={"company_currency": "PHP", "billing_currency": "USD", "billing_exchange_rate": 61.306},
	)
	def test_usd_billing_keeps_usd_line_rate(
		self,
		_mock_bctx,
		_mock_chr,
		_mock_exists,
		mock_get_doc,
		mock_new_doc,
		mock_get_meta,
		_mock_95,
		_mock_name,
		_mock_tbl,
		_mock_sv,
		_mock_commit,
	):
		job = self._mock_job()
		mock_get_doc.return_value = job

		si = MagicMock()
		si.items = []
		si.remarks = ""
		si.append = lambda field, row: si.items.append(frappe._dict(row))
		mock_new_doc.return_value = si

		meta = MagicMock()
		meta.get_field.return_value = None
		mock_get_meta.return_value = meta

		result = create_sales_invoice_from_job(
			job_type="Docket",
			job_name="PQ-TEST",
			customer="CUST-1",
			posting_date="2026-06-29",
			billing_currency="USD",
			exchange_rate=61.306,
			selected_charge_indices=json.dumps([0]),
		)

		self.assertTrue(result["ok"])
		self.assertEqual(si.currency, "USD")
		self.assertEqual(si.conversion_rate, 61.306)
		self.assertEqual(si.ignore_pricing_rule, 1)
		self.assertEqual(len(si.items), 1)
		self.assertEqual(si.items[0].rate, 500)

	@patch("logistics.invoice_integration.sales_invoice_api.frappe.db.commit")
	@patch("logistics.invoice_integration.sales_invoice_api.frappe.db.set_value")
	@patch("logistics.invoice_integration.sales_invoice_api.frappe.db.table_exists", return_value=True)
	@patch("logistics.invoice_integration.sales_invoice_api.ensure_sales_invoice_name_for_server_insert")
	@patch("logistics.invoice_integration.sales_invoice_api.apply_freight_95_post_missing_values")
	@patch("logistics.invoice_integration.sales_invoice_api.frappe.get_meta")
	@patch("logistics.invoice_integration.sales_invoice_api.frappe.new_doc")
	@patch("logistics.invoice_integration.sales_invoice_api.frappe.get_doc")
	@patch("logistics.invoice_integration.sales_invoice_api.frappe.db.exists", return_value=True)
	@patch("logistics.invoice_integration.sales_invoice_api.charge_to_company_rate_selling", return_value=61.306)
	@patch(
		"logistics.invoice_integration.sales_invoice_api._si_billing_context",
		return_value={"company_currency": "PHP", "billing_currency": "PHP", "billing_exchange_rate": 1.0},
	)
	def test_php_billing_converts_usd_charge(
		self,
		_mock_bctx,
		_mock_chr,
		_mock_exists,
		mock_get_doc,
		mock_new_doc,
		mock_get_meta,
		_mock_95,
		_mock_name,
		_mock_tbl,
		_mock_sv,
		_mock_commit,
	):
		job = self._mock_job()
		mock_get_doc.return_value = job

		si = MagicMock()
		si.items = []
		si.remarks = ""
		si.append = lambda field, row: si.items.append(frappe._dict(row))
		mock_new_doc.return_value = si

		meta = MagicMock()
		meta.get_field.return_value = None
		mock_get_meta.return_value = meta

		create_sales_invoice_from_job(
			job_type="Docket",
			job_name="PQ-TEST",
			customer="CUST-1",
			posting_date="2026-06-29",
			billing_currency="PHP",
			exchange_rate=1,
			selected_charge_indices=json.dumps([0]),
		)

		self.assertEqual(si.currency, "PHP")
		self.assertEqual(si.conversion_rate, 1)
		self.assertAlmostEqual(si.items[0].rate, flt(500 * 61.306), places=2)
