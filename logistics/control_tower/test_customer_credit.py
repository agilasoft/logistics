# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors

from __future__ import unicode_literals

import unittest

from logistics.control_tower.customer_credit import summarize_customer_credit


class TestCustomerCreditTotals(unittest.TestCase):
	def test_sums_limits_and_matching_positive_balances(self):
		totals = summarize_customer_credit(
			[
				{"parent": "CUST-1", "company": "Agila", "credit_limit": 1000},
				{"parent": "CUST-2", "company": "Agila", "credit_limit": 500},
			],
			[
				{"party": "CUST-1", "company": "Agila", "outstanding": 250},
				{"party": "CUST-2", "company": "Agila", "outstanding": 40},
				{"party": "CUST-9", "company": "Agila", "outstanding": 999},
			],
		)
		self.assertEqual(totals["limit"], 1500)
		self.assertEqual(totals["exposure"], 290)

	def test_ignores_credit_balances_and_other_companies(self):
		totals = summarize_customer_credit(
			[{"parent": "CUST-1", "company": "Agila", "credit_limit": 100}],
			[
				{"party": "CUST-1", "company": "Agila", "outstanding": -20},
				{"party": "CUST-1", "company": "Other", "outstanding": 80},
			],
		)
		self.assertEqual(totals["limit"], 100)
		self.assertEqual(totals["exposure"], 0)

	def test_limit_without_company_is_counted_but_not_matched(self):
		totals = summarize_customer_credit(
			[{"parent": "CUST-1", "company": None, "credit_limit": 75}],
			[{"party": "CUST-1", "company": "Agila", "outstanding": 75}],
		)
		self.assertEqual(totals["limit"], 75)
		self.assertEqual(totals["exposure"], 0)

	def test_does_not_double_count_the_same_customer_company(self):
		totals = summarize_customer_credit(
			[{"parent": "CUST-1", "company": "Agila", "credit_limit": 10}],
			[
				{"party": "CUST-1", "company": "Agila", "outstanding": 4},
				{"party": "CUST-1", "company": "Agila", "outstanding": 4},
			],
		)
		self.assertEqual(totals["exposure"], 4)
