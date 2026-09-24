# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Tests for Sales Invoice print line filters by Charge Type."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from logistics.print_format.sales_invoice.dsb_line_items import (
	get_disbursement_bill_context,
	get_disbursement_line_items,
	get_non_disbursement_line_items,
	get_sales_invoice_print_items,
	get_taxable_freight_line_items,
)


class _Item:
	def __init__(self, item_code, qty):
		self.item_code = item_code
		self.qty = qty


class _Invoice:
	def __init__(self, items):
		self.name = "ACC-SINV-0001"
		self.items = items


class TestNonDisbursementLineItems(unittest.TestCase):
	def _invoice(self):
		return _Invoice(
			[
				_Item("FREIGHT", 1),
				_Item("PERMITS", 1),
				_Item("OCEAN", 3),
			]
		)

	def test_matched_disbursement_charge_is_omitted(self):
		doc = self._invoice()
		with patch(
			"logistics.print_format.sales_invoice.dsb_line_items._collect_disbursement_charge_keys",
			return_value=[("PERMITS", 1.0)],
		):
			visible = get_non_disbursement_line_items(doc)
			hidden = get_disbursement_line_items(doc)

		self.assertEqual([item.item_code for item in visible], ["FREIGHT", "OCEAN"])
		self.assertEqual([item.item_code for item in hidden], ["PERMITS"])

	def test_item_default_fallback_omits_only_disbursement_defaults(self):
		doc = self._invoice()
		with patch(
			"logistics.print_format.sales_invoice.dsb_line_items._collect_disbursement_charge_keys",
			return_value=[],
		), patch(
			"logistics.print_format.sales_invoice.dsb_line_items._item_default_is_disbursement",
			side_effect=lambda item_code: item_code == "PERMITS",
		):
			visible = get_non_disbursement_line_items(doc)

		self.assertEqual([item.item_code for item in visible], ["FREIGHT", "OCEAN"])

	def test_empty_invoice_returns_no_lines(self):
		self.assertEqual(get_non_disbursement_line_items(_Invoice([])), [])


class TestSalesInvoicePrintItems(unittest.TestCase):
	def _invoice(self):
		return _Invoice(
			[
				_Item("FREIGHT", 1),
				_Item("TEST-AIR-FREIGHT", 1),
				_Item("PERMITS", 1),
				_Item("OCEAN", 3),
			]
		)

	def test_taxable_freight_item_stays_on_sales_invoice(self):
		doc = self._invoice()
		with patch(
			"logistics.print_format.sales_invoice.dsb_line_items._collect_disbursement_charge_keys",
			return_value=[],
		), patch(
			"logistics.print_format.sales_invoice.dsb_line_items._item_default_is_disbursement",
			return_value=False,
		), patch(
			"logistics.print_format.sales_invoice.dsb_line_items._collect_freight_95_main_item_keys",
			return_value=[],
		), patch(
			"logistics.print_format.sales_invoice.dsb_line_items._collect_taxable_freight_item_keys",
			return_value=[("TEST-AIR-FREIGHT", 1.0)],
		):
			visible = get_sales_invoice_print_items(doc)
			taxable = get_taxable_freight_line_items(doc)

		self.assertEqual(
			[item.item_code for item in visible],
			["FREIGHT", "TEST-AIR-FREIGHT", "PERMITS", "OCEAN"],
		)
		self.assertEqual([item.item_code for item in taxable], ["TEST-AIR-FREIGHT"])

	def test_disbursement_is_omitted_and_taxable_freight_item_stays(self):
		doc = self._invoice()
		with patch(
			"logistics.print_format.sales_invoice.dsb_line_items._collect_disbursement_charge_keys",
			return_value=[("PERMITS", 1.0)],
		), patch(
			"logistics.print_format.sales_invoice.dsb_line_items._collect_freight_95_main_item_keys",
			return_value=[],
		), patch(
			"logistics.print_format.sales_invoice.dsb_line_items._collect_taxable_freight_item_keys",
			return_value=[("TEST-AIR-FREIGHT", 1.0)],
		):
			visible = get_sales_invoice_print_items(doc)

		self.assertEqual(
			[item.item_code for item in visible],
			["FREIGHT", "TEST-AIR-FREIGHT", "OCEAN"],
		)

	def test_freight_95_main_line_is_on_bill_and_off_sales_invoice(self):
		doc = self._invoice()
		with patch(
			"logistics.print_format.sales_invoice.dsb_line_items._collect_disbursement_charge_keys",
			return_value=[("PERMITS", 1.0)],
		), patch(
			"logistics.print_format.sales_invoice.dsb_line_items._collect_freight_95_main_item_keys",
			return_value=[("FREIGHT", 1.0)],
		), patch(
			"logistics.print_format.sales_invoice.dsb_line_items._collect_taxable_freight_item_keys",
			return_value=[("TEST-AIR-FREIGHT", 1.0)],
		):
			visible = get_sales_invoice_print_items(doc)
			ctx = get_disbursement_bill_context(doc)

		self.assertEqual(
			[item.item_code for item in visible],
			["TEST-AIR-FREIGHT", "OCEAN"],
		)
		self.assertEqual(
			[item.item_code for item in ctx.line_items],
			["FREIGHT", "PERMITS"],
		)

	def test_bill_omits_taxable_freight_item(self):
		doc = self._invoice()
		with patch(
			"logistics.print_format.sales_invoice.dsb_line_items._collect_disbursement_charge_keys",
			return_value=[("PERMITS", 1.0)],
		), patch(
			"logistics.print_format.sales_invoice.dsb_line_items._collect_freight_95_main_item_keys",
			return_value=[],
		), patch(
			"logistics.print_format.sales_invoice.dsb_line_items._collect_taxable_freight_item_keys",
			return_value=[("TEST-AIR-FREIGHT", 1.0)],
		):
			ctx = get_disbursement_bill_context(doc)

		self.assertEqual([item.item_code for item in ctx.line_items], ["PERMITS"])
