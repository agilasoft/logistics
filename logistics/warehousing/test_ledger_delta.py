# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Warehouse Job submit posts Putaway, Pick, Move, and Stocktake with these signs."""

from __future__ import annotations

import unittest

from logistics.warehousing.ledger_delta import ledger_delta


class TestLedgerDelta(unittest.TestCase):
	def test_putaway_posts_positive(self):
		self.assertEqual(ledger_delta("Putaway", 4), (4, None))
		self.assertEqual(ledger_delta(" Putaway ", 1.5), (1.5, None))

	def test_putaway_and_pick_reject_non_positive(self):
		self.assertEqual(ledger_delta("Putaway", 0), (None, "positive_required"))
		self.assertEqual(ledger_delta("Putaway", -2), (None, "positive_required"))
		self.assertEqual(ledger_delta("Pick", 0), (None, "positive_required"))
		self.assertEqual(ledger_delta("Pick", -2), (None, "positive_required"))

	def test_pick_posts_negative(self):
		self.assertEqual(ledger_delta("Pick", 3), (-3, None))

	def test_move_posts_the_row_sign(self):
		self.assertEqual(ledger_delta("Move", 2), (2, None))
		self.assertEqual(ledger_delta("Move", -2), (-2, None))
		self.assertEqual(ledger_delta("Move", 0), (None, "nonzero_required"))

	def test_stocktake_posts_the_row_sign_including_zero(self):
		self.assertEqual(ledger_delta("Stocktake", 5), (5, None))
		self.assertEqual(ledger_delta("Stocktake", -5), (-5, None))
		self.assertEqual(ledger_delta("Stocktake", 0), (0, None))

	def test_other_types_post_the_row_sign(self):
		self.assertEqual(ledger_delta("Receiving", 6), (6, None))
		self.assertEqual(ledger_delta("Receiving", -1), (-1, None))
		self.assertEqual(ledger_delta("", 0), (None, "nonzero_required"))


if __name__ == "__main__":
	unittest.main()
