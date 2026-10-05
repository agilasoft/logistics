# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Customs Sales Quote charges keep the Declaration Charges unit types."""

from __future__ import annotations

import unittest

from logistics.pricing_center.sales_quote_customs_units import (
	customs_allowed_unit_types_text,
	customs_unit_type_problem,
)


class TestCustomsUnits(unittest.TestCase):
	def test_allowed_and_blank_units_pass(self):
		self.assertIsNone(customs_unit_type_problem("Job", "Value"))
		self.assertIsNone(customs_unit_type_problem(None, ""))
		self.assertIsNone(customs_unit_type_problem("Weight", None))

	def test_selling_unit_is_checked_before_cost_unit(self):
		self.assertEqual(customs_unit_type_problem("Pallet", "Day"), "unit_type")

	def test_cost_unit_is_checked_when_selling_unit_is_allowed(self):
		self.assertEqual(customs_unit_type_problem("TEU", "Pallet"), "cost_unit_type")

	def test_display_list_keeps_declaration_order(self):
		text = customs_allowed_unit_types_text()
		self.assertTrue(text.startswith('"Weight"'))
		self.assertIn('"Job"', text)
		self.assertTrue(text.endswith('"Value"'))


if __name__ == "__main__":
	unittest.main()
