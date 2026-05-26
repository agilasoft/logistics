# Copyright (c) 2025 Agilasoft. All rights reserved.
"""Smoke tests for driver mobile API alignment (no DB)."""

import importlib.util
from pathlib import Path
from unittest import TestCase

_api_py = Path(__file__).resolve().parents[2] / "api.py"
_spec = importlib.util.spec_from_file_location("logistics.transport._api_py_test", _api_py)
_api_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_api_mod)

RUN_SHEET_BUNDLE_LEG_FIELDS = _api_mod.RUN_SHEET_BUNDLE_LEG_FIELDS
DRIVER_LEG_UPDATE_FIELDS = _api_mod.DRIVER_LEG_UPDATE_FIELDS
_enrich_leg_for_mobile = _api_mod._enrich_leg_for_mobile


class TestDriverMobileAPIConstants(TestCase):
	def test_bundle_field_list_includes_mobile_fields(self):
		for field in (
			"pick_latitude",
			"pick_longitude",
			"pick_notes",
			"pick_photo",
			"drop_photo",
			"pick_signed_at",
			"drop_signed_at",
		):
			self.assertIn(field, RUN_SHEET_BUNDLE_LEG_FIELDS)

	def test_driver_update_allowlist(self):
		self.assertIn("pick_notes", DRIVER_LEG_UPDATE_FIELDS)
		self.assertIn("pick_photo", DRIVER_LEG_UPDATE_FIELDS)

	def test_enrich_leg_adds_aliases(self):
		leg = {"drop_signature": "x", "drop_signed_by": "y", "distance_km": 10}
		_enrich_leg_for_mobile(leg)
		self.assertEqual(leg["signature"], "x")
		self.assertEqual(leg["signed_by"], "y")
		self.assertEqual(leg["route_distance_km"], 10)
