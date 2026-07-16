# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

import frappe
from frappe.tests import UnitTestCase

from logistics.utils.commercial_invoice_totals import calculate_commercial_invoice_totals


def _doc(**kwargs):
	data = {
		"doctype": "Declaration Order",
		"inv_currency": "USD",
		"inv_total_amount": 0,
		"commercial_invoice_line_items": [],
		"commercial_invoice_charges": [],
	}
	data.update(kwargs)
	return data


class UnitTestCommercialInvoiceTotals(UnitTestCase):
	def test_line_items_only_set_fob_and_cif_to_line_total(self):
		totals = calculate_commercial_invoice_totals(
			_doc(
				commercial_invoice_line_items=[
					{"invoice_qty": 2, "price": 100},
					{"invoice_qty": 1, "price": 50},
				]
			)
		)
		self.assertEqual(totals["expected_invoice_line_total"], 250)
		self.assertEqual(totals["fob"], 250)
		self.assertEqual(totals["cif"], 250)

	def test_freight_and_insurance_increase_cif_not_fob(self):
		totals = calculate_commercial_invoice_totals(
			_doc(
				commercial_invoice_line_items=[{"invoice_qty": 1, "price": 1000}],
				commercial_invoice_charges=[
					{"charge_code": "OFT", "amount": 200, "currency": "USD"},
					{"charge_code": "ONS", "amount": 50, "currency": "USD"},
				],
			)
		)
		self.assertEqual(totals["fob"], 1000)
		self.assertEqual(totals["cif"], 1250)

	def test_add_to_fob_charge_increases_fob_and_cif(self):
		totals = calculate_commercial_invoice_totals(
			_doc(
				commercial_invoice_line_items=[{"invoice_qty": 1, "price": 1000}],
				commercial_invoice_charges=[
					{"charge_code": "LCH", "amount": 75, "currency": "USD", "add_to_fob": 1},
					{"charge_code": "OFT", "amount": 200, "currency": "USD"},
				],
			)
		)
		self.assertEqual(totals["fob"], 1075)
		self.assertEqual(totals["cif"], 1275)

	def test_deduction_charge_reduces_fob_and_cif(self):
		totals = calculate_commercial_invoice_totals(
			_doc(
				commercial_invoice_line_items=[{"invoice_qty": 1, "price": 1000}],
				commercial_invoice_charges=[{"charge_code": "DIS", "amount": 100, "currency": "USD"}],
			)
		)
		self.assertEqual(totals["fob"], 900)
		self.assertEqual(totals["cif"], 900)

	def test_included_in_inv_amt_charge_skipped_from_cif(self):
		totals = calculate_commercial_invoice_totals(
			_doc(
				inv_total_amount=1500,
				commercial_invoice_line_items=[{"invoice_qty": 1, "price": 1000}],
				commercial_invoice_charges=[
					{
						"charge_code": "OFT",
						"amount": 500,
						"currency": "USD",
						"included_in_inv_amt": 1,
					}
				],
			)
		)
		self.assertEqual(totals["cif"], 1000)

	def test_balance_matches_header_total_minus_allocated_amounts(self):
		totals = calculate_commercial_invoice_totals(
			_doc(
				inv_total_amount=1300,
				commercial_invoice_line_items=[{"invoice_qty": 1, "price": 1000}],
				commercial_invoice_charges=[{"charge_code": "OFT", "amount": 200, "currency": "USD"}],
			)
		)
		self.assertEqual(totals["balance"], "100.00")

	def test_charges_excl_from_itot_omits_charges_from_balance(self):
		totals = calculate_commercial_invoice_totals(
			_doc(
				inv_total_amount=1000,
				charges_excl_from_itot=1,
				commercial_invoice_line_items=[{"invoice_qty": 1, "price": 1000}],
				commercial_invoice_charges=[{"charge_code": "OFT", "amount": 200, "currency": "USD"}],
			)
		)
		self.assertEqual(totals["balance"], "0.00")
		self.assertEqual(totals["cif"], 1200)
