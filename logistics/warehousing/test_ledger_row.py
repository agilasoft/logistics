# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Warehouse Job submit requires a location and an item on every ledger row."""

from __future__ import annotations

import unittest

from logistics.warehousing.ledger_row import ledger_row_gap


class TestLedgerRow(unittest.TestCase):
	def test_complete_row_is_ready(self):
		self.assertIsNone(ledger_row_gap("A-01", "ITEM-1"))

	def test_missing_location_is_reported_first(self):
		self.assertEqual(ledger_row_gap(None, "ITEM-1"), "location")
		self.assertEqual(ledger_row_gap("", None), "location")

	def test_missing_item_is_reported_when_location_is_set(self):
		self.assertEqual(ledger_row_gap("A-01", None), "item")
		self.assertEqual(ledger_row_gap("A-01", ""), "item")


if __name__ == "__main__":
	unittest.main()
