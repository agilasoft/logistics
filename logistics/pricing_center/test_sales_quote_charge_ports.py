# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Submit still requires one complete Air or Sea charge corridor."""

from __future__ import annotations

import unittest

from logistics.pricing_center.sales_quote_charge_ports import air_sea_corridor_incomplete


class TestChargePorts(unittest.TestCase):
	def test_no_air_or_sea_charges_is_complete(self):
		self.assertFalse(air_sea_corridor_incomplete([], None, None))
		self.assertFalse(air_sea_corridor_incomplete(None, "MNL", "SIN"))

	def test_one_complete_row_is_enough(self):
		self.assertFalse(air_sea_corridor_incomplete([("MNL", None), ("MNL", "SIN")], None, None))

	def test_quote_ports_fill_a_blank_row(self):
		self.assertFalse(air_sea_corridor_incomplete([(None, None)], "MNL", "SIN"))
		self.assertFalse(air_sea_corridor_incomplete([("MNL", None)], None, "SIN"))

	def test_missing_both_ends_is_blocked(self):
		self.assertTrue(air_sea_corridor_incomplete([(None, "SIN"), ("MNL", None)], None, None))
		self.assertTrue(air_sea_corridor_incomplete([(None, None)], "MNL", None))


if __name__ == "__main__":
	unittest.main()
