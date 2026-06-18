# Copyright (c) 2026, AgilaSoft and contributors
# See license.txt

"""Tests for the small resolver helpers that live on the logistics side.

The live-AIS plumbing (providers, fallback, cache) belongs to the **GoConnect**
app and is exercised by its own tests; we only verify the leg-selection logic
and the dashboard-options surface here.
"""

from __future__ import unicode_literals

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.sea_freight.vessel_tracking.resolve import (
	get_vessel_tracking_map_options_for_sea_shipment,
	resolve_vessel_name_for_tracking_from_sea_shipment,
)


class TestVesselTrackingResolve(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	@patch("frappe.db.get_value")
	def test_resolve_prefers_main_sea_leg_vessel_master(self, mock_gv):
		def _gv(doctype, name, field, *args, **kwargs):
			if doctype == "Transport Mode" and field == "sea":
				return 1
			return None

		mock_gv.side_effect = _gv
		doc = frappe._dict(
			routing_legs=[
				frappe._dict(idx=1, mode="TM-SEA", type="Pre-carriage", vessel_master="VESSEL-PRE"),
				frappe._dict(idx=2, mode="TM-SEA", type="Main", vessel_master="VESSEL-MAIN"),
			]
		)
		self.assertEqual(resolve_vessel_name_for_tracking_from_sea_shipment(doc), "VESSEL-MAIN")

	@patch("frappe.db.get_value")
	def test_resolve_falls_back_to_first_sea_leg(self, mock_gv):
		def _gv(doctype, name, field, *args, **kwargs):
			if doctype == "Transport Mode" and field == "sea":
				return 1
			return None

		mock_gv.side_effect = _gv
		doc = frappe._dict(
			routing_legs=[
				frappe._dict(idx=1, mode="TM-SEA", type="Pre-carriage", vessel_master="VESSEL-FIRST"),
			]
		)
		self.assertEqual(resolve_vessel_name_for_tracking_from_sea_shipment(doc), "VESSEL-FIRST")


class TestGetVesselTrackingMapOptions(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_unsaved_doc_returns_disabled_with_hint(self):
		doc = frappe._dict(name=None, docstatus=0, routing_legs=[])
		out = get_vessel_tracking_map_options_for_sea_shipment(doc)
		self.assertFalse(out["enabled"])
		self.assertIn("Save the shipment", out["hint"])

	@patch(
		"logistics.sea_freight.vessel_tracking.resolve._goconnect_vessel_tracking_available",
		return_value=False,
	)
	def test_goconnect_not_configured_returns_hint(self, _mock_available):
		doc = frappe._dict(name="SS-1", docstatus=0, routing_legs=[])
		out = get_vessel_tracking_map_options_for_sea_shipment(doc)
		self.assertFalse(out["enabled"])
		self.assertIn("GoConnect", out["hint"])

	@patch(
		"logistics.sea_freight.vessel_tracking.resolve._goconnect_vessel_tracking_available",
		return_value=True,
	)
	@patch(
		"logistics.sea_freight.vessel_tracking.resolve._resolve_via_goconnect",
		return_value=None,
	)
	@patch(
		"logistics.sea_freight.vessel_tracking.resolve.resolve_vessel_name_for_tracking_from_sea_shipment",
		return_value=None,
	)
	def test_no_vessel_master_returns_hint(self, _resolve, _gc, _avail):
		doc = frappe._dict(name="SS-1", docstatus=0, routing_legs=[])
		out = get_vessel_tracking_map_options_for_sea_shipment(doc)
		self.assertFalse(out["enabled"])
		self.assertIn("Vessel Master", out["hint"])

	@patch(
		"logistics.sea_freight.vessel_tracking.resolve._goconnect_vessel_tracking_available",
		return_value=True,
	)
	@patch(
		"logistics.sea_freight.vessel_tracking.resolve._resolve_via_goconnect",
		return_value={"mmsi": "123456789", "imo": "9876543", "vessel": "Test"},
	)
	def test_enabled_when_goconnect_resolves(self, _gc, _avail):
		doc = frappe._dict(name="SS-1", docstatus=0, routing_legs=[])
		out = get_vessel_tracking_map_options_for_sea_shipment(doc)
		self.assertTrue(out["enabled"])
		self.assertEqual(out["sea_shipment"], "SS-1")
		self.assertIsNone(out["hint"])

	@patch(
		"logistics.sea_freight.vessel_tracking.resolve._goconnect_vessel_tracking_available",
		return_value=True,
	)
	@patch(
		"logistics.sea_freight.vessel_tracking.resolve._resolve_via_goconnect",
		return_value=None,
	)
	@patch(
		"logistics.sea_freight.vessel_tracking.resolve.resolve_vessel_name_for_tracking_from_sea_shipment",
		return_value="VESSEL-MAIN",
	)
	@patch(
		"logistics.sea_freight.vessel_tracking.resolve.get_vessel_ids_for_tracking",
		return_value=("123456789", "9876543", "Test Ship"),
	)
	def test_enabled_fallback_via_leg_when_goconnect_misses(self, _ids, _leg, _gc, _avail):
		doc = frappe._dict(name="SS-1", docstatus=0, routing_legs=[])
		out = get_vessel_tracking_map_options_for_sea_shipment(doc)
		self.assertTrue(out["enabled"])
		self.assertEqual(out["sea_shipment"], "SS-1")
		self.assertIsNone(out["hint"])
