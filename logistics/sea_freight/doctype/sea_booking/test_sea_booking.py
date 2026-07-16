# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from logistics.air_freight.tests.test_helpers import create_test_item

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class TestSeaBookingSalesQuoteChargeMapping(FrappeTestCase):
	"""Regression: Sales Quote Charge unit_rate must map to Sea Booking Charges unit_rate."""

	def _test_item_code(self):
		existing = frappe.db.get_value("Item", {"disabled": 0, "is_sales_item": 1}, "name")
		if existing:
			return existing
		return create_test_item(f"Sea Booking Map Test {frappe.generate_hash(length=6)}")

	def test_map_sales_quote_sea_freight_copies_unit_rate(self):
		item_code = self._test_item_code()
		booking = frappe.new_doc("Sea Booking")
		booking.total_weight = 100
		booking.total_volume = 1

		sq_row = {
			"item_code": item_code,
			"item_name": "Test Freight Charge",
			"revenue_calculation_method": "Per Unit",
			"unit_type": "Weight",
			"unit_rate": 250.5,
			"currency": "USD",
			"charge_type": "Revenue",
			"service_type": "Sea",
		}

		charge_data = booking._map_sales_quote_sea_freight_to_charge(sq_row)

		self.assertIsNotNone(charge_data)
		self.assertEqual(flt(charge_data.get("unit_rate")), 250.5)
		self.assertNotIn("rate", charge_data)

	def test_map_sales_quote_preserves_value_unit_type(self):
		"""Value (Percentage Break / goods-value) must copy through, not remap to Package."""
		item_code = self._test_item_code()
		booking = frappe.new_doc("Sea Booking")
		booking.total_weight = 100
		booking.total_volume = 1

		sq_row = {
			"item_code": item_code,
			"item_name": "Ad Valorem Charge",
			"revenue_calculation_method": "Percentage Break",
			"unit_type": "Value",
			"unit_rate": 1.5,
			"currency": "USD",
			"charge_type": "Both",
			"service_type": "Sea",
			"cost_calculation_method": "Percentage Break",
			"cost_unit_type": "Value",
			"unit_cost": 1.0,
		}

		charge_data = booking._map_sales_quote_sea_freight_to_charge(sq_row)

		self.assertIsNotNone(charge_data)
		self.assertEqual(charge_data.get("unit_type"), "Value")
		self.assertEqual(charge_data.get("cost_unit_type"), "Value")


class IntegrationTestSeaBooking(FrappeTestCase):
	"""
	Integration tests for SeaBooking.
	Use this class for testing interactions between multiple components.
	"""

	pass
