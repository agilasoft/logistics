# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""A time-sensitive Sales Quote requires a critical deadline."""

from __future__ import annotations

import unittest

from logistics.pricing_center.sales_quote_deadline import critical_deadline_missing


class TestCriticalDeadline(unittest.TestCase):
	def test_ordinary_quote_does_not_need_a_deadline(self):
		self.assertFalse(critical_deadline_missing(0, None))
		self.assertFalse(critical_deadline_missing(False, ""))

	def test_time_sensitive_quote_with_a_deadline_is_ready(self):
		self.assertFalse(critical_deadline_missing(1, "2026-10-04 12:00:00"))

	def test_time_sensitive_quote_without_a_deadline_is_blocked(self):
		self.assertTrue(critical_deadline_missing(1, None))
		self.assertTrue(critical_deadline_missing(1, ""))


if __name__ == "__main__":
	unittest.main()
