# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from logistics.air_freight.tests.test_helpers import create_test_item
from logistics.sea_freight.sea_freight_settings_defaults import (
	apply_incoterm_default_from_sea_freight_settings,
	apply_sea_booking_incoterm_defaults,
)

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


class TestSeaBookingIncotermPriority(FrappeTestCase):
	"""Incoterm: Sales Quote (overwrite) → Consignee → Shipper → Sea Freight Settings."""

	def _booking(self, *, shipper=None, consignee=None, company="Test Company"):
		booking = frappe.new_doc("Sea Booking")
		booking.company = company
		booking.shipper = shipper
		booking.consignee = consignee
		return booking

	def _party_docs(self, *, consignee_incoterm=None, shipper_incoterm=None):
		consignee = frappe._dict(default_incoterm=consignee_incoterm)
		shipper = frappe._dict(default_incoterm=shipper_incoterm)

		def _get_cached_doc(doctype, name):
			if doctype == "Consignee":
				return consignee
			if doctype == "Shipper":
				return shipper
			raise AssertionError(f"Unexpected get_cached_doc({doctype!r}, {name!r})")

		return _get_cached_doc

	def _run_priority(self, booking, sales_quote, settings, *, consignee_incoterm=None, shipper_incoterm=None):
		with (
			patch(
				"logistics.utils.shipper_consignee_defaults.frappe.get_cached_doc",
				side_effect=self._party_docs(
					consignee_incoterm=consignee_incoterm,
					shipper_incoterm=shipper_incoterm,
				),
			),
			patch(
				"logistics.sea_freight.sea_freight_settings_defaults._get_sea_freight_settings_for_doc",
				return_value=settings,
			),
			patch("frappe.db.exists", return_value=True),
		):
			apply_sea_booking_incoterm_defaults(booking, sales_quote=sales_quote)

	def test_quote_incoterm_wins_over_party_and_settings(self):
		booking = self._booking(shipper="S1", consignee="C1")
		self._run_priority(
			booking,
			frappe._dict(incoterm="FOB"),
			frappe._dict(default_incoterm="CIF"),
			consignee_incoterm="EXW",
			shipper_incoterm="FCA",
		)
		self.assertEqual(booking.incoterm, "FOB")

	def test_quote_overwrites_existing_consignee_fob(self):
		"""Linked quote Incoterm always wins even when booking already has Consignee FOB."""
		booking = self._booking(shipper="S1", consignee="C1")
		booking.incoterm = "FOB"
		self._run_priority(
			booking,
			frappe._dict(incoterm="EXW"),
			frappe._dict(default_incoterm="CIF"),
			consignee_incoterm="FOB",
			shipper_incoterm="FCA",
		)
		self.assertEqual(booking.incoterm, "EXW")

	def test_consignee_default_when_quote_blank(self):
		booking = self._booking(shipper="S1", consignee="C1")
		self._run_priority(
			booking,
			frappe._dict(incoterm=None),
			frappe._dict(default_incoterm="CIF"),
			consignee_incoterm="EXW",
			shipper_incoterm="FCA",
		)
		self.assertEqual(booking.incoterm, "EXW")

	def test_shipper_default_when_quote_and_consignee_blank(self):
		booking = self._booking(shipper="S1", consignee="C1")
		self._run_priority(
			booking,
			frappe._dict(incoterm=None),
			frappe._dict(default_incoterm="CIF"),
			consignee_incoterm=None,
			shipper_incoterm="FCA",
		)
		self.assertEqual(booking.incoterm, "FCA")

	def test_settings_default_is_last_priority(self):
		booking = self._booking(shipper="S1", consignee="C1")
		self._run_priority(
			booking,
			frappe._dict(incoterm=None),
			frappe._dict(default_incoterm="CIF"),
			consignee_incoterm=None,
			shipper_incoterm=None,
		)
		self.assertEqual(booking.incoterm, "CIF")

	def test_settings_does_not_overwrite_existing_incoterm(self):
		booking = self._booking()
		booking.incoterm = "DAP"
		settings = frappe._dict(default_incoterm="CIF")

		with (
			patch(
				"logistics.sea_freight.sea_freight_settings_defaults._get_sea_freight_settings_for_doc",
				return_value=settings,
			),
			patch("frappe.db.exists", return_value=True),
		):
			apply_incoterm_default_from_sea_freight_settings(booking)

		self.assertEqual(booking.incoterm, "DAP")


class IntegrationTestSeaBooking(FrappeTestCase):
	"""
	Integration tests for SeaBooking.
	Use this class for testing interactions between multiple components.
	"""

	pass
