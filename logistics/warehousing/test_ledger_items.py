# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Warehouse Job submit blocks an empty item list, except a prepared Stocktake."""

from __future__ import annotations

import unittest

from logistics.warehousing.ledger_items import empty_ledger_items_reason


class TestLedgerItems(unittest.TestCase):
	def test_rows_are_ready_to_post(self):
		self.assertIsNone(empty_ledger_items_reason("Putaway", True))
		self.assertIsNone(empty_ledger_items_reason("Pick", True, False))
		self.assertIsNone(empty_ledger_items_reason("Stocktake", True, False))

	def test_empty_stocktake_needs_populate_or_rows(self):
		self.assertEqual(
			empty_ledger_items_reason("Stocktake", False, False),
			"populate_or_add",
		)
		self.assertEqual(empty_ledger_items_reason(" Stocktake ", False), "populate_or_add")
		self.assertEqual(empty_ledger_items_reason("Stocktake", False, 0), "populate_or_add")

	def test_prepared_stocktake_may_post_with_no_rows(self):
		self.assertIsNone(empty_ledger_items_reason("Stocktake", False, True))
		self.assertIsNone(empty_ledger_items_reason("Stocktake", False, 1))

	def test_other_empty_jobs_need_rows(self):
		self.assertEqual(empty_ledger_items_reason("Putaway", False), "items_required")
		self.assertEqual(empty_ledger_items_reason("Move", False, True), "items_required")
		self.assertEqual(empty_ledger_items_reason("", False), "items_required")
		self.assertEqual(empty_ledger_items_reason(None, None), "items_required")


if __name__ == "__main__":
	unittest.main()
