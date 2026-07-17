# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Unit tests for routing leg connecting-port defaults."""

import unittest

from logistics.utils.routing_leg_connecting_port import (
	apply_connecting_port_default_to_row,
	connecting_start_port_for_new_leg,
)


class TestRoutingLegConnectingPort(unittest.TestCase):
	def test_air_shipment_second_leg_gets_previous_discharge(self):
		legs = [
			{"name": "leg1", "idx": 1, "load_port": "PHCBT", "discharge_port": "PHMNL"},
			{"name": "leg2", "idx": 2, "load_port": None, "discharge_port": None},
		]
		self.assertEqual(
			connecting_start_port_for_new_leg(
				legs,
				"leg2",
				parent_doctype="Air Shipment",
			),
			"PHMNL",
		)

	def test_asp_000000359_style_third_leg(self):
		"""Same port chain as ASP-000000359 when adding a new empty third leg."""
		legs = [
			{"name": "kon1m87ogb", "idx": 1, "load_port": "PHCBT", "discharge_port": "PHMNL"},
			{"name": "konflfio7m", "idx": 2, "load_port": "PHMNL", "discharge_port": "SGCHG"},
			{"name": "newleg3", "idx": 3, "load_port": None, "discharge_port": None},
		]
		self.assertEqual(
			connecting_start_port_for_new_leg(
				legs,
				"newleg3",
				child_doctype="Air Shipment Routing Leg",
			),
			"SGCHG",
		)

	def test_does_not_overwrite_existing_load_port(self):
		legs = [
			{"name": "leg1", "idx": 1, "load_port": "PHCBT", "discharge_port": "PHMNL"},
			{"name": "leg2", "idx": 2, "load_port": "SGSIN", "discharge_port": None},
		]
		self.assertIsNone(
			connecting_start_port_for_new_leg(
				legs,
				"leg2",
				parent_doctype="Air Shipment",
			)
		)

	def test_first_leg_has_no_default(self):
		legs = [{"name": "leg1", "idx": 1, "load_port": None, "discharge_port": None}]
		self.assertIsNone(
			connecting_start_port_for_new_leg(
				legs,
				"leg1",
				parent_doctype="Air Booking",
			)
		)

	def test_sales_quote_uses_destination_to_origin(self):
		legs = [
			{"name": "leg1", "idx": 1, "origin": "PHMNL", "destination": "SGSIN"},
			{"name": "leg2", "idx": 2, "origin": None, "destination": None},
		]
		self.assertEqual(
			connecting_start_port_for_new_leg(
				legs,
				"leg2",
				parent_doctype="Sales Quote",
			),
			"SGSIN",
		)

	def test_apply_mutates_row(self):
		leg2 = {"name": "leg2", "idx": 2, "load_port": None, "discharge_port": None}
		legs = [
			{"name": "leg1", "idx": 1, "load_port": "A", "discharge_port": "B"},
			leg2,
		]
		self.assertEqual(
			apply_connecting_port_default_to_row(legs, leg2, parent_doctype="Sea Booking"),
			"B",
		)
		self.assertEqual(leg2["load_port"], "B")

	def test_previous_discharge_empty_yields_none(self):
		legs = [
			{"name": "leg1", "idx": 1, "load_port": "A", "discharge_port": None},
			{"name": "leg2", "idx": 2, "load_port": None, "discharge_port": None},
		]
		self.assertIsNone(
			connecting_start_port_for_new_leg(
				legs,
				"leg2",
				parent_doctype="Sea Shipment",
			)
		)
