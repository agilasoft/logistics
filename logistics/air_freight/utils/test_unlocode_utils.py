# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

import unittest
from unittest.mock import patch

from logistics.air_freight.utils.unlocode_utils import (
	enrich_country_info,
	get_unlocode_data,
	infer_unlocode_data,
	parse_un_coordinates,
	unwrap_populate_result,
)


class TestParseUnCoordinates(unittest.TestCase):
	def test_los_angeles(self):
		lat, lon = parse_un_coordinates("3342N 11824W")
		self.assertAlmostEqual(lat, 33.0 + 42.0 / 60.0, places=5)
		self.assertAlmostEqual(lon, -(118.0 + 24.0 / 60.0), places=5)

	def test_andorra(self):
		lat, lon = parse_un_coordinates("4230N 00131E")
		self.assertAlmostEqual(lat, 42.0 + 30.0 / 60.0, places=5)
		self.assertAlmostEqual(lon, 1.0 + 31.0 / 60.0, places=5)

	def test_sydney_quadrant(self):
		lat, lon = parse_un_coordinates("3351S 15112E")
		self.assertLess(lat, 0)
		self.assertGreater(lon, 0)

	def test_flexible_space(self):
		lat, lon = parse_un_coordinates("  3342N   11824W  ")
		self.assertIsNotNone(lat)
		self.assertIsNotNone(lon)

	def test_lowercase_hemisphere(self):
		lat, lon = parse_un_coordinates("3342n 11824w")
		self.assertAlmostEqual(lat, 33.0 + 42.0 / 60.0, places=5)
		self.assertAlmostEqual(lon, -(118.0 + 24.0 / 60.0), places=5)

	def test_equator_zero_latitude_valid(self):
		# Parsed 0.0 latitude must be valid (truthy checks elsewhere must not drop it)
		lat, lon = parse_un_coordinates("0000N 00100E")
		self.assertAlmostEqual(lat, 0.0, places=5)
		self.assertAlmostEqual(lon, 1.0 + 0.0 / 60.0, places=5)

	def test_empty(self):
		self.assertEqual(parse_un_coordinates(""), (None, None))
		self.assertEqual(parse_un_coordinates(None), (None, None))

	def test_malformed(self):
		self.assertEqual(parse_un_coordinates("invalid"), (None, None))


class TestUnwrapPopulateResult(unittest.TestCase):
	def test_wrapped(self):
		self.assertEqual(
			unwrap_populate_result({"status": "success", "data": {"latitude": 1.0, "longitude": 2.0}}),
			{"latitude": 1.0, "longitude": 2.0},
		)

	def test_flat_legacy(self):
		d = {"location_name": "X", "latitude": 3.0}
		self.assertEqual(unwrap_populate_result(d), d)

	def test_empty(self):
		self.assertEqual(unwrap_populate_result(None), {})
		self.assertEqual(unwrap_populate_result({}), {})


class TestEnrichCountryInfo(unittest.TestCase):
	@patch("frappe.db.get_value")
	def test_frappe_country_lookup(self, mock_gv):
		mock_gv.return_value = "Philippines"
		d = enrich_country_info("PH")
		self.assertEqual(d["country_code"], "PH")
		self.assertEqual(d["country"], "Philippines")
		mock_gv.assert_called_once()

	@patch("frappe.db.get_value")
	def test_hardcoded_skips_db_when_mapped(self, mock_gv):
		d = enrich_country_info("US")
		self.assertEqual(d["country"], "United States")
		self.assertEqual(d["country_code"], "US")
		mock_gv.assert_not_called()


class TestInferUnlocodeData(unittest.TestCase):
	@patch("frappe.db.get_value")
	def test_infer_does_not_abort_for_unmapped_iso2(self, mock_gv):
		mock_gv.return_value = "Philippines"
		d = infer_unlocode_data("PHMNL")
		self.assertIsNotNone(d)
		self.assertEqual(d.get("country_code"), "PH")
		self.assertEqual(d.get("country"), "Philippines")
		self.assertEqual(d.get("location_type"), "Other")


class TestDatahubResourceUrls(unittest.TestCase):
	def test_datapackage_relative_paths_resolve_to_datahub(self):
		from logistics.air_freight.utils.datahub_unlocode import DATAHUB_UN_LOCODE_DATASET, _merge_resource_urls

		dp = {
			"resources": [
				{"name": "code-list", "path": "data/code-list.csv"},
				{"name": "country-codes", "path": "data/country-codes.csv"},
				{"name": "status-indicators", "path": "data/status-indicators.csv"},
			]
		}
		urls = _merge_resource_urls(dp)
		prefix = DATAHUB_UN_LOCODE_DATASET.rstrip("/") + "/"
		self.assertTrue(urls["code-list"].startswith(prefix))
		self.assertTrue(urls["code-list"].endswith("code-list.csv"))
		self.assertTrue(urls["country-codes"].endswith("country-codes.csv"))


class TestGetUnlocodeDataMerge(unittest.TestCase):
	"""Stored UNLOCO rows must not block country fill when Populate runs."""

	def _sparse_db_row(self, country="", country_code=""):
		row = [None] * 28
		row[0] = "NLRTM"
		row[1] = "Rotterdam"
		row[2] = country
		row[3] = country_code
		for i in range(17, 28):
			row[i] = 0
		return tuple(row)

	@patch("logistics.air_freight.utils.unlocode_utils.get_unlocode_from_database")
	@patch("frappe.db.get_value")
	def test_merges_country_from_overlay(self, mock_gv, mock_fresh):
		mock_gv.return_value = self._sparse_db_row()
		mock_fresh.return_value = {
			"location_name": "Rotterdam",
			"country": "Netherlands",
			"country_code": "NL",
			"location_type": "Port",
			"data_source": "DataHub.io",
		}
		d = get_unlocode_data("NLRTM")
		self.assertIsNotNone(d)
		self.assertEqual(d.get("country"), "Netherlands")
		self.assertEqual(d.get("country_code"), "NL")

	@patch("logistics.air_freight.utils.unlocode_utils.get_unlocode_from_database")
	@patch("frappe.db.get_value")
	def test_backfills_from_iso2_when_no_overlay(self, mock_gv, mock_fresh):
		mock_gv.return_value = self._sparse_db_row()
		mock_fresh.return_value = None
		d = get_unlocode_data("NLRTM")
		self.assertEqual(d.get("country_code"), "NL")
		self.assertEqual(d.get("country"), "Netherlands")

	def _sparse_db_row_ph(self):
		row = [None] * 28
		row[0] = "PHMNL"
		row[1] = "Manila"
		row[2] = ""
		row[3] = ""
		for i in range(17, 28):
			row[i] = 0
		return tuple(row)

	@patch("logistics.air_freight.utils.unlocode_utils.get_unlocode_from_database")
	@patch("frappe.db.get_value")
	def test_backfills_ph_via_frappe_country(self, mock_gv, mock_fresh):
		mock_fresh.return_value = None

		def gv(*args, **kwargs):
			if args and args[0] == "UNLOCO":
				return self._sparse_db_row_ph()
			if args and args[0] == "Country":
				return "Philippines"
			return None

		mock_gv.side_effect = gv
		d = get_unlocode_data("PHMNL")
		self.assertEqual(d.get("country_code"), "PH")
		self.assertEqual(d.get("country"), "Philippines")
