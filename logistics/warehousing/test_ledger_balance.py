# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Warehouse Job submit blocks an outbound post that would finish below zero."""

from __future__ import annotations

import unittest

from logistics.warehousing.ledger_balance import ledger_balance_after_post


class TestLedgerBalance(unittest.TestCase):
	def test_outbound_that_stays_at_or_above_zero_posts(self):
		self.assertEqual(ledger_balance_after_post(10, -3), (7, False))
		self.assertEqual(ledger_balance_after_post(10, -10), (0, False))

	def test_outbound_below_zero_is_blocked(self):
		self.assertEqual(ledger_balance_after_post(10, -11), (-1, True))
		self.assertEqual(ledger_balance_after_post(0, -1), (-1, True))

	def test_inbound_from_zero_posts(self):
		self.assertEqual(ledger_balance_after_post(0, 5), (5, False))
		self.assertEqual(ledger_balance_after_post(None, 4), (4, False))

	def test_zero_delta_is_not_an_outbound_block(self):
		self.assertEqual(ledger_balance_after_post(0, 0), (0, False))


if __name__ == "__main__":
	unittest.main()
