# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Unit tests for main-job routing operational overlay (#936)."""

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import cint

from logistics.utils.sales_quote_routing import (
	_find_matching_main_job_routing_leg,
	apply_main_job_routing_operational_overlay,
)


class TestSalesQuoteRoutingOverlay(FrappeTestCase):
	def test_find_matching_leg_by_ports(self):
		booking_leg = frappe._dict(
			load_port="USLAX",
			discharge_port="USJFK",
			transport_mode_sea=1,
			transport_mode_air=0,
		)
		main_legs = [
			frappe._dict(
				idx=1,
				load_port="USLAX",
				discharge_port="USJFK",
				transport_mode_sea=1,
				vessel="MV TEST",
			),
			frappe._dict(
				idx=2,
				load_port="CNSHA",
				discharge_port="USLAX",
				transport_mode_sea=1,
			),
		]
		match = _find_matching_main_job_routing_leg(booking_leg, main_legs)
		self.assertEqual(getattr(match, "vessel", None), "MV TEST")

	def test_apply_overlay_sets_sea_fields_on_booking_doc(self):
		booking = frappe.new_doc("Air Booking")
		booking.is_internal_job = 1
		booking.main_job_type = "Sea Shipment"
		booking.main_job = "SH-TEST-OVERLAY"
		booking.append(
			"routing_legs",
			{
				"mode": "Sea",
				"type": "Main",
				"load_port": "USLAX",
				"discharge_port": "USJFK",
				"transport_mode_sea": 1,
				"transport_mode_air": 0,
			},
		)
		main = frappe.new_doc("Sea Shipment")
		main.name = "SH-TEST-OVERLAY"
		main.append(
			"routing_legs",
			{
				"type": "Main",
				"load_port": "USLAX",
				"discharge_port": "USJFK",
				"transport_mode_sea": 1,
				"vessel": "VESSEL-X",
				"voyage_no": "VY-1",
			},
		)

		class _FakeDB:
			@staticmethod
			def exists(doctype, name):
				return doctype == "Sea Shipment" and name == "SH-TEST-OVERLAY"

		orig_get_doc = frappe.get_doc
		orig_exists = frappe.db.exists

		def _get_doc(dt, name=None, *args, **kwargs):
			if dt == "Sea Shipment" and name == "SH-TEST-OVERLAY":
				return main
			return orig_get_doc(dt, name, *args, **kwargs)

		frappe.get_doc = _get_doc
		frappe.db.exists = _FakeDB.exists
		try:
			applied = apply_main_job_routing_operational_overlay(booking)
		finally:
			frappe.get_doc = orig_get_doc
			frappe.db.exists = orig_exists

		self.assertTrue(applied)
		leg = booking.routing_legs[0]
		self.assertEqual(leg.vessel, "VESSEL-X")
		self.assertEqual(leg.voyage_no, "VY-1")
		self.assertEqual(cint(leg.transport_mode_sea), 1)


if __name__ == "__main__":
	unittest.main()
