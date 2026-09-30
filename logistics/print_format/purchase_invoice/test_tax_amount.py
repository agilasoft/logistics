"""Printed tax sign on Purchase Invoice and Debit Note."""

from __future__ import annotations

import unittest

from logistics.print_format.purchase_invoice.tax_amount import printed_tax_amount


class TestPrintedTaxAmount(unittest.TestCase):
	def test_debit_note_withholding_is_negative(self):
		self.assertEqual(
			printed_tax_amount(-39, is_debit_note=True, label="Withholding Tax Payable - ATN"),
			-39,
		)
		self.assertEqual(
			printed_tax_amount(39, is_debit_note=True, label="Withholding Tax Payable - ATN"),
			-39,
		)

	def test_debit_note_other_tax_stays_positive(self):
		self.assertEqual(
			printed_tax_amount(-12, is_debit_note=True, label="VAT 12%"),
			12,
		)

	def test_purchase_invoice_withholding_stays_signed(self):
		self.assertEqual(
			printed_tax_amount(-39, label="Withholding Tax Payable - ATN"),
			-39,
		)

	def test_credit_note_withholding_stays_positive(self):
		self.assertEqual(
			printed_tax_amount(-39, is_credit_note=True, label="Withholding Tax Payable - ATN"),
			39,
		)
