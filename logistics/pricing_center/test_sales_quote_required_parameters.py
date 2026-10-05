# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Sales Quote scope validation lists the missing fields in form order."""

from __future__ import annotations

import unittest

from logistics.pricing_center.sales_quote_required_parameters import (
	missing_one_off_scope_fields,
	missing_programme_scope_fields,
)


class TestSalesQuoteRequiredParameters(unittest.TestCase):
	def test_air_and_sea_require_ports(self):
		values = {"destination_port": "MNL"}
		self.assertEqual(
			missing_one_off_scope_fields("One-off", "Air", 0, values),
			["origin_port"],
		)
		self.assertEqual(
			missing_one_off_scope_fields("Regular", "Sea", 0, {}),
			["origin_port", "destination_port"],
		)
		self.assertEqual(
			missing_one_off_scope_fields("One-off", "Air", 0, {
				"origin_port": "LAX",
				"destination_port": "MNL",
			}),
			[],
		)

	def test_transport_requires_locations(self):
		self.assertEqual(
			missing_one_off_scope_fields("Regular", "Transport", 0, {"location_type": "Door"}),
			["location_from", "location_to"],
		)

	def test_mice_requires_show_and_dates(self):
		self.assertEqual(
			missing_one_off_scope_fields("One-off", "MICE", 0, {"exhibit": "  "}),
			["exhibit", "exhibit_show_open_date", "exhibit_show_close_date"],
		)
		self.assertEqual(
			missing_programme_scope_fields("MICE", 0, {"exhibit": "SHOW-1"}),
			["exhibit_show_open_date", "exhibit_show_close_date"],
		)

	def test_additional_charge_and_other_types_skip_scope(self):
		empty = {}
		self.assertEqual(missing_one_off_scope_fields("One-off", "Air", 1, empty), [])
		self.assertEqual(missing_one_off_scope_fields("Project", "Air", 0, empty), [])
		self.assertEqual(missing_one_off_scope_fields("Regular", "Warehousing", 0, empty), [])
		self.assertEqual(missing_programme_scope_fields("MICE", 1, empty), [])
		self.assertEqual(missing_programme_scope_fields("Air", 0, empty), [])


if __name__ == "__main__":
	unittest.main()
