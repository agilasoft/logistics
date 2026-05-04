# Copyright (c) 2026, AgilaSoft and contributors
# See license.txt

from __future__ import unicode_literals

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.sea_freight.vessel_tracking.providers.normalize import pick_coords
from logistics.sea_freight.vessel_tracking.resolve import (
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


class TestNormalizePickCoords(FrappeTestCase):
	def test_pick_coords_latitude_longitude(self):
		lat, lon = pick_coords({"latitude": 12.5, "longitude": 100.25})
		self.assertEqual(lat, 12.5)
		self.assertEqual(lon, 100.25)

	def test_pick_coords_lat_lng(self):
		lat, lon = pick_coords({"lat": -36.8, "lng": 174.7})
		self.assertAlmostEqual(lat, -36.8)
		self.assertAlmostEqual(lon, 174.7)


class TestGetVesselPositionAPI(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	@patch("frappe.cache")
	@patch("logistics.sea_freight.vessel_tracking.api._run_provider")
	@patch("logistics.sea_freight.vessel_tracking.api.sea_freight_settings_allow_tracking")
	@patch("logistics.sea_freight.vessel_tracking.api.resolve_vessel_name_for_tracking_from_sea_shipment")
	@patch("logistics.sea_freight.vessel_tracking.api.get_vessel_ids_for_tracking")
	@patch("logistics.sea_freight.vessel_tracking.api.SeaFreightSettings.get_settings")
	def test_get_vessel_position_maps_provider_response(
		self,
		mock_get_settings,
		mock_get_ids,
		mock_resolve,
		mock_allow,
		mock_run,
		mock_cache_fn,
	):
		mock_allow.return_value = True
		mock_resolve.return_value = "TEST-VSL"
		mock_get_ids.return_value = ("123456789", None, "Test Ship")
		settings = MagicMock()
		settings.vessel_tracking_provider = "VesselAPI"
		settings.get_password.return_value = "fake-key"
		mock_get_settings.return_value = settings
		norm = {
			"lat": 1.234,
			"lon": 103.456,
			"label": "API Name",
			"sog": 12.0,
			"cog": 90.0,
			"recorded_at": "2026-01-01T00:00:00Z",
			"source": "VesselAPI",
			"raw": {},
		}
		mock_run.return_value = norm
		mock_cache_fn.return_value.get_value.return_value = None

		sh = frappe._dict(
			name="SS-MAP-TEST",
			company="_Test Company",
			docstatus=0,
			routing_legs=[],
		)
		from logistics.sea_freight.vessel_tracking import api as vt_api

		with patch.object(vt_api.frappe, "get_doc", return_value=sh):
			with patch.object(vt_api.frappe, "has_permission", return_value=True):
				out = vt_api.get_vessel_position_for_map("SS-MAP-TEST")
		self.assertTrue(out.get("success"))
		self.assertEqual(out.get("lat"), 1.234)
		self.assertEqual(out.get("lon"), 103.456)
