# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import unittest

import frappe
from frappe.utils import flt

from logistics.invoice_integration.charge_settled_reversal import (
	compute_item_reversal_amount,
	get_charge_items_settled_by_sales_invoice,
	recognition_reversal_tolerance,
)
from logistics.utils.freight_95_5 import resolve_sales_invoice_line_qty_rate


class TestComputeItemReversalAmount(unittest.TestCase):
	def test_settled_charge_reverses_full_open_wip_not_invoice_amount(self):
		"""SF000000268 pattern: WIP 312.50 recognized, SI 312.00 — clear full open."""
		settled = {"TRNSFR"}
		rev = compute_item_reversal_amount(
			312.0, 312.5, 1000.0, "TRNSFR", settled, "Test Company"
		)
		self.assertEqual(rev, 312.5)

	def test_partial_invoice_without_settled_charge(self):
		settled = set()
		rev = compute_item_reversal_amount(
			100.0, 500.0, 500.0, "FREIGHT", settled, "Test Company"
		)
		self.assertEqual(rev, 100.0)

	def test_only_linked_item_cleared_when_two_items(self):
		settled = {"ITEM-A"}
		rev_a = compute_item_reversal_amount(
			50.0, 312.5, 1000.0, "ITEM-A", settled, "Test Company"
		)
		rev_b = compute_item_reversal_amount(
			50.0, 312.5, 1000.0, "ITEM-B", settled, "Test Company"
		)
		self.assertEqual(rev_a, 312.5)
		self.assertEqual(rev_b, 50.0)

	def test_rounding_tolerance_clears_near_match_without_charge_link(self):
		settled = set()
		open_item = 312.5
		company = "Test Company"
		tol = recognition_reversal_tolerance(company, open_item)
		amt = open_item - tol
		rev = compute_item_reversal_amount(
			amt, open_item, 1000.0, "TRNSFR", settled, company
		)
		self.assertEqual(rev, open_item)

	def test_respects_remaining_job_wip_cap(self):
		settled = {"TRNSFR"}
		rev = compute_item_reversal_amount(
			312.0, 312.5, 50.0, "TRNSFR", settled, "Test Company"
		)
		self.assertEqual(rev, 50.0)


class TestGetChargeItemsSettledBySalesInvoice(unittest.TestCase):
	def test_collects_item_codes_from_linked_charge_rows(self):
		job = frappe._dict(
			doctype="Sea Shipment",
			name="SF000000001",
			charges=[
				frappe._dict(
					item_code="TRNSFR",
					sales_invoice="ACC-SINV-2026-00001",
				),
				frappe._dict(
					item_code="FREIGHT",
					sales_invoice=None,
				),
				frappe._dict(
					item_code="TRNSFR CHRG",
					sales_invoice="ACC-SINV-2026-00001",
				),
			],
		)
		items = get_charge_items_settled_by_sales_invoice(job, "ACC-SINV-2026-00001")
		self.assertEqual(items, {"TRNSFR", "TRNSFR CHRG"})


class TestResolveSalesInvoiceLineQtyRate(unittest.TestCase):
	def test_per_unit_aligns_qty_when_quantity_times_rate_differs_from_revenue(self):
		"""Charge quantity 0.13 × rate 2500 ≠ 312.5; SI should use qty 0.125 × 2500."""
		charge = frappe._dict(
			revenue_calculation_method="Per Unit",
			quantity=0.13,
			rate=2500.0,
			estimated_revenue=312.5,
		)
		qty, rate, revenue = resolve_sales_invoice_line_qty_rate(charge, None, None)
		self.assertEqual(revenue, 312.5)
		self.assertEqual(rate, 2500.0)
		self.assertAlmostEqual(flt(qty) * flt(rate), 312.5, places=2)
		self.assertAlmostEqual(flt(qty), 0.125, places=3)

	def test_per_unit_keeps_charge_qty_when_product_matches_revenue(self):
		charge = frappe._dict(
			revenue_calculation_method="Per Unit",
			quantity=2.0,
			rate=100.0,
			estimated_revenue=200.0,
		)
		qty, rate, revenue = resolve_sales_invoice_line_qty_rate(charge, None, None)
		self.assertEqual((qty, rate, revenue), (2.0, 100.0, 200.0))

	def test_fixed_amount_uses_single_line_rate(self):
		charge = frappe._dict(
			revenue_calculation_method="Fixed Amount",
			estimated_revenue=500.0,
		)
		qty, rate, revenue = resolve_sales_invoice_line_qty_rate(charge, None, None)
		self.assertIsNone(qty)
		self.assertIsNone(rate)
		self.assertEqual(revenue, 500.0)
