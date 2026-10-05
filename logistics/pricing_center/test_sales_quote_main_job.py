# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Multimodal Sales Quote routing requires one Main Job leg."""

from __future__ import annotations

import unittest

from logistics.pricing_center.sales_quote_main_job import multimodal_main_job_missing


class TestMainJob(unittest.TestCase):
	def test_no_legs_is_not_multimodal(self):
		self.assertFalse(multimodal_main_job_missing([]))
		self.assertFalse(multimodal_main_job_missing(None))

	def test_a_main_job_leg_is_enough(self):
		self.assertFalse(multimodal_main_job_missing([0, 1, 0]))

	def test_legs_without_a_main_job_are_blocked(self):
		self.assertTrue(multimodal_main_job_missing([0, 0]))
		self.assertTrue(multimodal_main_job_missing([None, ""]))


if __name__ == "__main__":
	unittest.main()
