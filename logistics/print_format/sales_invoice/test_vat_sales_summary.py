# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Tests for Sales Invoice HTML VAT buckets from the tax template."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from logistics.print_format.sales_invoice.vat_sales_summary import (
	get_vat_sales_summary,
	item_is_zero_rated_or_exempt,
)


class _Row:
	def __init__(self, **kwargs):
		self.__dict__.update(kwargs)


class _FakeInvoice:
	def __init__(self, items=None, taxes=None, **kwargs):
		self.items = items or []
		self.taxes = taxes or []
		self.net_total = 0
		self.tax_category = None
		self.taxes_and_charges = None
		self.__dict__.update(kwargs)


class TestVatSalesSummary(unittest.TestCase):
	def setUp(self):
		self.db_patch = patch(
			"logistics.print_format.sales_invoice.vat_sales_summary.frappe.db.get_value",
			return_value=None,
		)
		self.db_patch.start()
		self.addCleanup(self.db_patch.stop)

	def test_vatable_template_puts_net_total_in_vatable(self):
		inv = _FakeInvoice(
			net_total=2646.0,
			tax_category="Vatable",
			taxes_and_charges="Philippines Tax",
			taxes=[_Row(account_head="VAT - ASL", description="VAT - ASL", rate=12, net_amount=0, tax_amount=324)],
		)
		summary = get_vat_sales_summary(inv)
		self.assertAlmostEqual(summary.vatable_sales, 2646.0)
		self.assertAlmostEqual(summary.exempt_sales, 0)
		self.assertAlmostEqual(summary.zero_rated_sales, 0)
		self.assertAlmostEqual(summary.total_sales, 2646.0)

	def test_exempt_tax_account_puts_net_total_in_exempt(self):
		inv = _FakeInvoice(
			net_total=500.0,
			taxes=[_Row(account_head="Exempt Sales", description="VAT Exempt", rate=0, net_amount=0)],
		)
		summary = get_vat_sales_summary(inv)
		self.assertAlmostEqual(summary.exempt_sales, 500.0)
		self.assertAlmostEqual(summary.vatable_sales, 0)
		self.assertAlmostEqual(summary.zero_rated_sales, 0)
		self.assertAlmostEqual(summary.total_sales, 500.0)

	def test_zero_rated_tax_account_puts_net_total_in_zero_rated(self):
		inv = _FakeInvoice(
			net_total=750.0,
			taxes=[_Row(account_head="Zero Rated Output", description="Zero Rated", rate=0, net_amount=0)],
		)
		summary = get_vat_sales_summary(inv)
		self.assertAlmostEqual(summary.zero_rated_sales, 750.0)
		self.assertAlmostEqual(summary.vatable_sales, 0)
		self.assertAlmostEqual(summary.exempt_sales, 0)
		self.assertAlmostEqual(summary.total_sales, 750.0)

	def test_exempt_tax_category_when_taxes_have_no_vat_label(self):
		inv = _FakeInvoice(
			net_total=400.0,
			tax_category="VAT Exempt",
			taxes=[_Row(account_head="Sales", description="Sales", rate=0, net_amount=0)],
		)
		summary = get_vat_sales_summary(inv)
		self.assertAlmostEqual(summary.exempt_sales, 400.0)
		self.assertAlmostEqual(summary.vatable_sales, 0)

	def test_zero_rated_tax_category_when_taxes_have_no_vat_label(self):
		inv = _FakeInvoice(
			net_total=300.0,
			tax_category="Zero Rated",
			taxes=[],
		)
		summary = get_vat_sales_summary(inv)
		self.assertAlmostEqual(summary.zero_rated_sales, 300.0)
		self.assertAlmostEqual(summary.vatable_sales, 0)

	def test_template_tax_category_used_when_invoice_category_blank(self):
		inv = _FakeInvoice(
			net_total=180.0,
			taxes_and_charges="VAT Exempt Template",
			taxes=[],
		)
		with patch(
			"logistics.print_format.sales_invoice.vat_sales_summary._template_hints",
			return_value=["VAT Exempt Template", "VAT Exempt", "Exempt Sales"],
		):
			summary = get_vat_sales_summary(inv)
		self.assertAlmostEqual(summary.exempt_sales, 180.0)
		self.assertAlmostEqual(summary.vatable_sales, 0)

	def test_withholding_row_is_ignored(self):
		inv = _FakeInvoice(
			net_total=1000.0,
			tax_category="Vatable",
			taxes=[
				_Row(account_head="VAT - ASL", description="VAT - ASL", rate=12, net_amount=0, tax_amount=120),
				_Row(
					account_head="EWT Payable",
					description="Withholding Tax",
					rate=1,
					net_amount=0,
					tax_amount=10,
					is_withholding_tax=1,
				),
			],
		)
		summary = get_vat_sales_summary(inv)
		self.assertAlmostEqual(summary.vatable_sales, 1000.0)
		self.assertAlmostEqual(summary.exempt_sales, 0)
		self.assertAlmostEqual(summary.zero_rated_sales, 0)

	def test_withholding_label_without_flag_is_ignored(self):
		inv = _FakeInvoice(
			net_total=200.0,
			tax_category="Vatable",
			taxes=[_Row(account_head="Expanded Withholding Tax", description="EWT", rate=2, net_amount=0)],
		)
		summary = get_vat_sales_summary(inv)
		self.assertAlmostEqual(summary.vatable_sales, 200.0)
		self.assertAlmostEqual(summary.exempt_sales, 0)

	def test_mixed_rows_split_by_net_amount(self):
		inv = _FakeInvoice(
			net_total=1400.0,
			taxes=[
				_Row(account_head="VAT - ASL", description="VAT", rate=12, net_amount=1000.0),
				_Row(account_head="Exempt Sales", description="VAT Exempt", rate=0, net_amount=400.0),
			],
		)
		summary = get_vat_sales_summary(inv)
		self.assertAlmostEqual(summary.vatable_sales, 1000.0)
		self.assertAlmostEqual(summary.exempt_sales, 400.0)
		self.assertAlmostEqual(summary.zero_rated_sales, 0)
		self.assertAlmostEqual(summary.total_sales, 1400.0)

	def test_mixed_rows_without_net_amount_fall_back_to_item_templates(self):
		inv = _FakeInvoice(
			net_total=900.0,
			items=[
				_Row(net_amount=600.0, item_tax_template="VAT 12%"),
				_Row(net_amount=300.0, item_tax_template="Zero Rated"),
			],
			taxes=[
				_Row(account_head="VAT - ASL", description="VAT", rate=12, net_amount=0),
				_Row(account_head="Zero Rated Output", description="Zero Rated", rate=0, net_amount=0),
			],
		)
		summary = get_vat_sales_summary(inv)
		self.assertAlmostEqual(summary.vatable_sales, 600.0)
		self.assertAlmostEqual(summary.zero_rated_sales, 300.0)
		self.assertAlmostEqual(summary.exempt_sales, 0)

	def test_unclassified_taxes_fall_back_to_net_total_as_vatable(self):
		inv = _FakeInvoice(
			net_total=50.0,
			taxes=[_Row(account_head="Freight", description="Freight", rate=0, net_amount=0)],
		)
		summary = get_vat_sales_summary(inv)
		self.assertAlmostEqual(summary.vatable_sales, 50.0)
		self.assertAlmostEqual(summary.exempt_sales, 0)
		self.assertAlmostEqual(summary.zero_rated_sales, 0)

	def test_mixed_invoice_splits_exempt_item_tax_template_from_vatable(self):
		inv = _FakeInvoice(
			net_total=600900.0,
			tax_category="Vatable",
			items=[
				_Row(net_amount=550900.0),
				_Row(net_amount=50000.0, item_tax_template="VAT Exempt"),
			],
			taxes=[_Row(account_head="VAT - ASL", description="VAT - ASL", rate=12, net_amount=0, tax_amount=66108)],
		)

		def rates(name):
			if name == "VAT Exempt":
				return [{"tax_type": "VAT - Exempt - ASL", "tax_rate": 0, "not_applicable": 0}]
			return []

		with patch(
			"logistics.print_format.sales_invoice.vat_sales_summary._item_tax_template_rates",
			side_effect=rates,
		):
			summary = get_vat_sales_summary(inv)
		self.assertAlmostEqual(summary.vatable_sales, 484792.0)
		self.assertAlmostEqual(summary.exempt_sales, 50000.0)
		self.assertAlmostEqual(summary.zero_rated_sales, 0)
		self.assertAlmostEqual(summary.total_sales, 534792.0)

	def test_exempt_tax_rate_counts_when_template_title_has_no_exempt(self):
		inv = _FakeInvoice(
			net_total=50000.0,
			items=[_Row(net_amount=50000.0, item_tax_template="Philippines Tax - ASL")],
			taxes=[_Row(account_head="VAT - ASL", description="VAT - ASL", rate=12, net_amount=0, tax_amount=6000)],
		)
		with patch(
			"logistics.print_format.sales_invoice.vat_sales_summary._item_tax_template_rates",
			return_value=[{"tax_type": "VAT - Exempt - ASL", "tax_rate": 0, "not_applicable": 0}],
		):
			summary = get_vat_sales_summary(inv)
		self.assertAlmostEqual(summary.exempt_sales, 50000.0)
		self.assertAlmostEqual(summary.vatable_sales, 0)
		self.assertAlmostEqual(summary.zero_rated_sales, 0)
		self.assertAlmostEqual(summary.total_sales, 50000.0)

	def test_mixed_invoice_splits_zero_rated_item_tax_template_from_vatable(self):
		inv = _FakeInvoice(
			net_total=650000.0,
			tax_category="Vatable",
			items=[
				_Row(net_amount=100000.0),
				_Row(net_amount=550000.0, item_tax_template="Zero Rated"),
			],
			taxes=[_Row(account_head="VAT - ASL", description="VAT - ASL", rate=12, net_amount=0, tax_amount=12000)],
		)

		def rates(name):
			if name == "Zero Rated":
				return [{"tax_type": "Zero - Rated - ASL", "tax_rate": 0, "not_applicable": 0}]
			return []

		with patch(
			"logistics.print_format.sales_invoice.vat_sales_summary._item_tax_template_rates",
			side_effect=rates,
		):
			summary = get_vat_sales_summary(inv)
		self.assertAlmostEqual(summary.vatable_sales, 88000.0)
		self.assertAlmostEqual(summary.zero_rated_sales, 550000.0)
		self.assertAlmostEqual(summary.exempt_sales, 0)
		self.assertAlmostEqual(summary.total_sales, 638000.0)

	def test_zero_rated_tax_rate_counts_when_template_title_has_no_zero_rated(self):
		inv = _FakeInvoice(
			net_total=550000.0,
			items=[_Row(net_amount=550000.0, item_tax_template="Philippines Tax - ASL")],
			taxes=[_Row(account_head="VAT - ASL", description="VAT - ASL", rate=12, net_amount=0, tax_amount=0)],
		)
		with patch(
			"logistics.print_format.sales_invoice.vat_sales_summary._item_tax_template_rates",
			return_value=[{"tax_type": "Zero - Rated - ASL", "tax_rate": 0, "not_applicable": 0}],
		):
			summary = get_vat_sales_summary(inv)
		self.assertAlmostEqual(summary.zero_rated_sales, 550000.0)
		self.assertAlmostEqual(summary.vatable_sales, 0)
		self.assertAlmostEqual(summary.exempt_sales, 0)
		self.assertAlmostEqual(summary.total_sales, 550000.0)

	def test_zero_rated_sales_uses_row_amount_from_item_tax_rate(self):
		inv = _FakeInvoice(
			net_total=550000.0,
			items=[
				_Row(
					amount=550000.0,
					item_tax_template="Zero Rated - ASL",
					item_tax_rate='{"Zero - Rated - ASL": 0}',
				)
			],
			taxes=[_Row(account_head="VAT - ASL", description="VAT - ASL", rate=12, net_amount=0)],
		)
		summary = get_vat_sales_summary(inv)
		self.assertAlmostEqual(summary.zero_rated_sales, 550000.0)
		self.assertAlmostEqual(summary.vatable_sales, 0)
		self.assertAlmostEqual(summary.exempt_sales, 0)
		self.assertAlmostEqual(summary.total_sales, 550000.0)

	def test_mixed_exempt_and_zero_rated_row_amounts(self):
		inv = _FakeInvoice(
			net_total=650000.0,
			items=[
				_Row(
					amount=100000.0,
					item_tax_template="VAT Exempt",
					item_tax_rate='{"VAT - Exempt - ASL": 0}',
				),
				_Row(
					amount=550000.0,
					item_tax_template="Zero Rated - ASL",
					item_tax_rate='{"Zero - Rated - ASL": 0}',
				),
			],
			taxes=[_Row(account_head="VAT - ASL", description="VAT - ASL", rate=12, net_amount=0)],
		)
		summary = get_vat_sales_summary(inv)
		self.assertAlmostEqual(summary.exempt_sales, 100000.0)
		self.assertAlmostEqual(summary.zero_rated_sales, 550000.0)
		self.assertAlmostEqual(summary.vatable_sales, 0)
		self.assertAlmostEqual(summary.total_sales, 650000.0)

	def test_vatable_line_uses_print_amount_net_minus_tax(self):
		inv = _FakeInvoice(
			net_total=490.0,
			items=[
				_Row(
					net_amount=490.0,
					custom_tax_amount=60.0,
					item_tax_template="Philippines Tax - ASL",
				)
			],
			taxes=[_Row(account_head="VAT - ASL", description="VAT - ASL", rate=12, net_amount=0, tax_amount=60)],
		)
		with patch(
			"logistics.print_format.sales_invoice.vat_sales_summary._item_tax_template_rates",
			return_value=[{"tax_type": "VAT - ASL", "tax_rate": 12, "not_applicable": 0}],
		):
			summary = get_vat_sales_summary(inv)
		self.assertAlmostEqual(summary.vatable_sales, 430.0)
		self.assertAlmostEqual(summary.exempt_sales, 0)
		self.assertAlmostEqual(summary.zero_rated_sales, 0)
		self.assertAlmostEqual(summary.total_sales, 430.0)


class TestItemIsZeroRatedOrExempt(unittest.TestCase):
	def setUp(self):
		self.db_patch = patch(
			"logistics.print_format.sales_invoice.vat_sales_summary.frappe.db.get_value",
			return_value=None,
		)
		self.db_patch.start()
		self.addCleanup(self.db_patch.stop)

	def test_zero_rated_item_tax_template(self):
		inv = _FakeInvoice(
			net_total=980.0,
			tax_category="Vatable",
			items=[_Row(net_amount=980.0, item_tax_template="Zero Rated")],
			taxes=[_Row(account_head="VAT - ASL", description="VAT - ASL", rate=12, net_amount=0)],
		)
		with patch(
			"logistics.print_format.sales_invoice.vat_sales_summary._item_tax_template_rates",
			return_value=[{"tax_type": "Zero - Rated - ASL", "tax_rate": 0, "not_applicable": 0}],
		):
			self.assertTrue(item_is_zero_rated_or_exempt(inv, inv.items[0]))

	def test_exempt_item_tax_template(self):
		inv = _FakeInvoice(
			net_total=500.0,
			tax_category="Vatable",
			items=[_Row(net_amount=500.0, item_tax_template="VAT Exempt")],
			taxes=[_Row(account_head="VAT - ASL", description="VAT - ASL", rate=12, net_amount=0)],
		)
		with patch(
			"logistics.print_format.sales_invoice.vat_sales_summary._item_tax_template_rates",
			return_value=[{"tax_type": "VAT - Exempt - ASL", "tax_rate": 0, "not_applicable": 0}],
		):
			self.assertTrue(item_is_zero_rated_or_exempt(inv, inv.items[0]))

	def test_exempt_item_tax_rate(self):
		inv = _FakeInvoice(
			net_total=100000.0,
			items=[
				_Row(
					amount=100000.0,
					item_tax_template="VAT Exempt",
					item_tax_rate='{"VAT - Exempt - ASL": 0}',
				)
			],
			taxes=[_Row(account_head="VAT - ASL", description="VAT - ASL", rate=12, net_amount=0)],
		)
		self.assertTrue(item_is_zero_rated_or_exempt(inv, inv.items[0]))

	def test_vatable_template_with_zero_tax_is_false(self):
		inv = _FakeInvoice(
			net_total=980.0,
			tax_category="Vatable",
			items=[
				_Row(
					net_amount=980.0,
					custom_tax_amount=0.0,
					item_tax_template="Philippines Tax - ASL",
				)
			],
			taxes=[_Row(account_head="VAT - ASL", description="VAT - ASL", rate=12, net_amount=0, tax_amount=0)],
		)
		with patch(
			"logistics.print_format.sales_invoice.vat_sales_summary._item_tax_template_rates",
			return_value=[{"tax_type": "VAT - ASL", "tax_rate": 12, "not_applicable": 0}],
		):
			self.assertFalse(item_is_zero_rated_or_exempt(inv, inv.items[0]))

	def test_invoice_level_vat_exempt_marks_all_lines(self):
		inv = _FakeInvoice(
			net_total=400.0,
			tax_category="VAT Exempt",
			items=[_Row(net_amount=250.0), _Row(net_amount=150.0)],
			taxes=[_Row(account_head="Sales", description="Sales", rate=0, net_amount=0)],
		)
		self.assertTrue(item_is_zero_rated_or_exempt(inv, inv.items[0]))
		self.assertTrue(item_is_zero_rated_or_exempt(inv, inv.items[1]))

	def test_invoice_level_zero_rated_marks_all_lines(self):
		inv = _FakeInvoice(
			net_total=300.0,
			tax_category="Zero Rated",
			items=[_Row(net_amount=300.0)],
			taxes=[],
		)
		self.assertTrue(item_is_zero_rated_or_exempt(inv, inv.items[0]))
