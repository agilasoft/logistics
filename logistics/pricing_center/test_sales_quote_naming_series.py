# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Sales Quote naming series prefixes stay tied to the quotation type."""

from __future__ import annotations

import unittest

from logistics.pricing_center.sales_quote_naming_series import naming_series_mismatch


class TestSalesQuoteNamingSeries(unittest.TestCase):
	def test_dot_and_hyphen_prefixes_match(self):
		self.assertIsNone(naming_series_mismatch("Regular", "SQU.#########"))
		self.assertIsNone(naming_series_mismatch("Regular", "SQU-.#####"))
		self.assertIsNone(naming_series_mismatch("One-off", "OOQ.#####"))
		self.assertIsNone(naming_series_mismatch("One-off", "OOQ-#####"))
		self.assertIsNone(naming_series_mismatch("Project", "PQ.#####"))
		self.assertIsNone(naming_series_mismatch("Project", "PQ-#####"))

	def test_wrong_prefix_reports_the_expected_series(self):
		self.assertEqual(
			naming_series_mismatch("Regular", "OOQ.#####"),
			{"expected_display": "SQU. / SQU-", "expected_example": "SQU.#########"},
		)
		self.assertEqual(
			naming_series_mismatch("One-off", "PQ.#####"),
			{"expected_display": "OOQ. / OOQ-", "expected_example": "OOQ.#####"},
		)
		self.assertEqual(
			naming_series_mismatch("Project", "SQU.#########"),
			{"expected_display": "PQ. / PQ-", "expected_example": "PQ.#####"},
		)

	def test_empty_and_unknown_types_are_accepted(self):
		self.assertIsNone(naming_series_mismatch("", "SQU.#########"))
		self.assertIsNone(naming_series_mismatch("Regular", ""))
		self.assertIsNone(naming_series_mismatch(None, None))
		self.assertIsNone(naming_series_mismatch("Blanket", "SQU.#########"))


if __name__ == "__main__":
	unittest.main()
