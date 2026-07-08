# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Tests for Sales Quote routing leg defaults (#1120)."""

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.air_freight.tests.test_helpers import create_test_consignee, create_test_shipper
from logistics.utils.sales_quote_routing_defaults import (
	apply_sales_quote_routing_defaults,
	suggest_sales_quote_routing_legs,
)


class TestSalesQuoteRoutingDefaults(FrappeTestCase):
	def setUp(self):
		self.shipper = create_test_shipper("SQ-RT-SHIP", "SQ Routing Shipper")
		self.consignee = create_test_consignee("SQ-RT-CONS", "SQ Routing Consignee")

	def test_single_main_leg_when_party_ports_match_corridor(self):
		legs = suggest_sales_quote_routing_legs(
			shipper=self.shipper,
			consignee=self.consignee,
			origin_port="USLAX",
			destination_port="USJFK",
			main_service="Air",
			transport_mode="Air",
		)
		self.assertEqual(len(legs), 1)
		self.assertEqual(legs[0]["type"], "Main")
		self.assertEqual(legs[0]["origin"], "USLAX")
		self.assertEqual(legs[0]["destination"], "USJFK")
		self.assertEqual(legs[0]["is_main_job"], 1)

	def test_pre_and_on_forwarding_from_party_default_ports(self):
		frappe.db.set_value("Shipper", self.shipper, "default_airport", "USORD")
		frappe.db.set_value("Consignee", self.consignee, "default_airport", "USMIA")
		legs = suggest_sales_quote_routing_legs(
			shipper=self.shipper,
			consignee=self.consignee,
			origin_port="USLAX",
			destination_port="USJFK",
			main_service="Air",
			transport_mode="Air",
		)
		self.assertEqual(len(legs), 3)
		self.assertEqual(legs[0]["type"], "Pre-carriage")
		self.assertEqual(legs[0]["origin"], "USORD")
		self.assertEqual(legs[0]["destination"], "USLAX")
		self.assertEqual(legs[1]["type"], "Main")
		self.assertEqual(legs[1]["is_main_job"], 1)
		self.assertEqual(legs[2]["type"], "On-forwarding")
		self.assertEqual(legs[2]["origin"], "USJFK")
		self.assertEqual(legs[2]["destination"], "USMIA")

	def test_apply_defaults_on_sales_quote_validate(self):
		sq = frappe.new_doc("Sales Quote")
		sq.quotation_type = "Regular"
		sq.main_service = "Air"
		sq.naming_series = "SQU.#########"
		sq.shipper = self.shipper
		sq.consignee = self.consignee
		sq.origin_port = "USLAX"
		sq.destination_port = "USJFK"
		sq.transport_mode = "Air"
		applied = apply_sales_quote_routing_defaults(sq)
		self.assertTrue(applied)
		self.assertEqual(len(sq.routing_legs), 1)
		self.assertEqual(sq.routing_legs[0].origin, "USLAX")

	def test_does_not_overwrite_existing_legs_without_force(self):
		sq = frappe.new_doc("Sales Quote")
		sq.quotation_type = "Regular"
		sq.main_service = "Air"
		sq.shipper = self.shipper
		sq.consignee = self.consignee
		sq.origin_port = "USLAX"
		sq.destination_port = "USJFK"
		sq.append(
			"routing_legs",
			{"mode": "Air", "type": "Main", "is_main_job": 1, "origin": "CNSHA", "destination": "SGSIN"},
		)
		applied = apply_sales_quote_routing_defaults(sq)
		self.assertFalse(applied)
		self.assertEqual(sq.routing_legs[0].origin, "CNSHA")
