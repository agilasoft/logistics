# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from logistics.utils.measurements import compute_density_factor, get_density_factor_api


class TestDensityFactor(FrappeTestCase):
	@patch("logistics.utils.measurements.convert_weight", side_effect=lambda value, **kwargs: value)
	@patch("logistics.utils.measurements.convert_volume", side_effect=lambda value, **kwargs: value)
	@patch(
		"logistics.utils.measurements.get_base_uoms",
		return_value={"dimension": "Centimeter", "volume": "Cubic Meter", "weight": "Kilogram"},
	)
	def test_fractional_cubic_meters_not_rounded_to_zero(self, _base, _cv, _cw):
		"""Regression: flt(volume, 0) rounded 0.24 m³ to 0 and showed density 0.0."""
		df = compute_density_factor(0.24, 25.0)
		self.assertIsNotNone(df)
		self.assertAlmostEqual(df, 9600.0, places=1)

	@patch("logistics.utils.measurements.convert_weight", side_effect=lambda value, **kwargs: value)
	@patch("logistics.utils.measurements.convert_volume", side_effect=lambda value, **kwargs: value)
	@patch(
		"logistics.utils.measurements.get_base_uoms",
		return_value={"dimension": "Centimeter", "volume": "Cubic Meter", "weight": "Kilogram"},
	)
	def test_api_returns_volumetric_for_abk_style_inputs(self, _base, _cv, _cw):
		result = get_density_factor_api(volume=0.24, weight=25.0)
		self.assertIsNone(result.get("reason"))
		self.assertAlmostEqual(flt(result["density_factor"]), 9600.0, places=1)
		self.assertEqual(flt(result["percent"]), 100.0)

	def test_zero_weight_returns_none(self):
		self.assertIsNone(compute_density_factor(0.24, 0))
