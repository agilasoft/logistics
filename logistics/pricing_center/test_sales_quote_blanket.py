# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Blanket Sales Quotes stay on Regular quotes that are not additional charges."""

from __future__ import annotations

import unittest

from logistics.pricing_center.sales_quote_blanket import blanket_quotation_block


class TestBlanketQuotation(unittest.TestCase):
	def test_unchecked_blanket_is_allowed(self):
		self.assertIsNone(blanket_quotation_block(0, "One-off", 1, 1, False))

	def test_regular_draft_with_no_charges_is_allowed(self):
		self.assertIsNone(blanket_quotation_block(1, " Regular ", 0, 0, False))

	def test_non_regular_is_blocked(self):
		self.assertEqual(blanket_quotation_block(1, "One-off", 0, 0, True), "not_regular")
		self.assertEqual(blanket_quotation_block(1, None, 0, 0, True), "not_regular")

	def test_additional_charge_is_blocked(self):
		self.assertEqual(blanket_quotation_block(1, "Regular", 1, 0, True), "additional_charge")

	def test_submitted_blanket_without_charges_is_blocked(self):
		self.assertEqual(blanket_quotation_block(1, "Regular", 0, 1, False), "missing_charges")
		self.assertIsNone(blanket_quotation_block(1, "Regular", 0, 1, True))


if __name__ == "__main__":
	unittest.main()
