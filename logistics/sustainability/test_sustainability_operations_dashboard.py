# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

import unittest

from logistics.sustainability import sustainability_operations_dashboard as dashboard
from logistics.sustainability.sustainability_operations_dashboard import (
	build_lanes,
	emission_band,
	lane_identity,
	parse_choice,
	parse_period,
	summarize,
)


def _row(**kwargs):
	base = {
		"name": "CF-1",
		"date": "2026-04-01",
		"module": "Air Freight",
		"facility": "",
		"scope": "Scope 3",
		"total_emissions": 0,
		"net_emissions": 0,
		"carbon_offset": 0,
		"origin": "",
		"destination": "",
		"reference_doctype": "Air Shipment",
		"reference_name": "AS-1",
	}
	base.update(kwargs)
	return base


class TestSustainabilityOperationsDashboard(unittest.TestCase):
	def test_emission_color_follows_carbon_footprint_rating_cutoffs(self):
		self.assertEqual(emission_band(0)["key"], "excellent")
		self.assertEqual(emission_band(100)["label"], "Excellent")
		self.assertEqual(emission_band(100)["color"], "#15803d")
		self.assertEqual(emission_band(100.01)["key"], "good")
		self.assertEqual(emission_band(500)["key"], "good")
		self.assertEqual(emission_band(500.01)["key"], "fair")
		self.assertEqual(emission_band(1000)["key"], "fair")
		self.assertEqual(emission_band(1000.01)["key"], "poor")
		self.assertEqual(emission_band(2000)["key"], "poor")
		self.assertEqual(emission_band(2000.01)["label"], "Very Poor")
		self.assertEqual(emission_band(2000.01)["color"], "#b91c1c")
		self.assertEqual(emission_band(-5)["key"], "excellent")

	def test_route_identity_needs_two_different_ends(self):
		route = lane_identity("Air Freight", "SGSIN", "PHMNL", "MNL DC")
		self.assertEqual(route["kind"], "route")
		self.assertEqual(route["label"], "SGSIN → PHMNL")
		same = lane_identity("Air Freight", "SGSIN", "SGSIN", "MNL DC")
		self.assertEqual(same["kind"], "facility")
		self.assertEqual(same["label"], "SGSIN")
		facility = lane_identity("Warehousing", "", "", "MNL DC")
		self.assertEqual(facility["label"], "MNL DC")
		module = lane_identity("Customs", "", "", "")
		self.assertEqual(module["kind"], "module")
		self.assertEqual(module["label"], "Customs")

	def test_lanes_group_routes_and_color_by_total_emissions(self):
		records = [
			_row(name="A", origin="SGSIN", destination="PHMNL", total_emissions=80, net_emissions=70, carbon_offset=10),
			_row(name="B", origin="SGSIN", destination="PHMNL", total_emissions=50, net_emissions=50, reference_name="AS-2"),
			_row(
				name="C",
				origin="USLAX",
				destination="JPTYO",
				total_emissions=2500,
				net_emissions=2500,
				reference_name="AS-3",
			),
			_row(
				name="D",
				module="Warehousing",
				facility="MNL DC",
				origin="",
				destination="",
				total_emissions=40,
				net_emissions=40,
				reference_doctype="Warehouse Job",
				reference_name="WJ-1",
			),
		]
		lanes, total = build_lanes(records, limit=10)
		self.assertEqual(total, 3)
		self.assertEqual(lanes[0]["label"], "USLAX → JPTYO")
		self.assertEqual(lanes[0]["band"], "very_poor")
		self.assertEqual(lanes[0]["color"], "#b91c1c")
		self.assertEqual(lanes[0]["bar_pct"], 100)
		sin = next(lane for lane in lanes if lane["label"] == "SGSIN → PHMNL")
		self.assertEqual(sin["count"], 2)
		self.assertEqual(sin["emissions"], 130)
		self.assertEqual(sin["band"], "good")
		self.assertEqual(sin["color"], "#4d7c0f")
		self.assertEqual(len(sin["records"]), 2)
		dc = next(lane for lane in lanes if lane["label"] == "MNL DC")
		self.assertEqual(dc["kind"], "facility")
		self.assertEqual(dc["band"], "excellent")

	def test_lane_limit_keeps_hottest_first(self):
		records = [
			_row(name="LOW", origin="AAAAA", destination="BBBBB", total_emissions=10),
			_row(name="HIGH", origin="CCCCC", destination="DDDDD", total_emissions=3000),
		]
		lanes, total = build_lanes(records, limit=1)
		self.assertEqual(total, 2)
		self.assertEqual(len(lanes), 1)
		self.assertEqual(lanes[0]["label"], "CCCCC → DDDDD")

	def test_high_share_uses_poor_and_very_poor_lanes(self):
		records = [
			_row(name="HOT", origin="USLAX", destination="JPTYO", total_emissions=2500, net_emissions=2400, carbon_offset=100),
			_row(name="COOL", origin="SGSIN", destination="PHMNL", total_emissions=100, net_emissions=100),
		]
		lanes, _total = build_lanes(records, limit=10)
		kpis = summarize(records, lanes)
		self.assertEqual(kpis["high_lanes"], 1)
		self.assertEqual(kpis["records"], 2)
		self.assertEqual(kpis["emissions"], 2600)
		self.assertAlmostEqual(kpis["high_share"], round(2500 / 2600 * 100, 1))

	def test_sum_totals_uses_aggregate_dict_fields(self):
		captured = {}

		class FakeFrappe:
			def get_all(self, doctype, filters=None, fields=None, **kwargs):
				captured["doctype"] = doctype
				captured["filters"] = filters
				captured["fields"] = fields
				captured["kwargs"] = kwargs
				return [{"records": 3, "emissions": 10.5, "net": 8, "offset": 2.5}]

		original = dashboard._frappe
		dashboard._frappe = lambda: FakeFrappe()
		try:
			totals = dashboard._sum_totals({"company": "ACME", "date": [">=", "2026-01-01"]})
		finally:
			dashboard._frappe = original

		self.assertEqual(captured["doctype"], "Carbon Footprint")
		self.assertEqual(captured["filters"]["company"], "ACME")
		self.assertEqual(
			captured["fields"],
			[
				{"COUNT": "name", "as": "records"},
				{"SUM": "total_emissions", "as": "emissions"},
				{"SUM": "net_emissions", "as": "net"},
				{"SUM": "carbon_offset", "as": "offset"},
			],
		)
		self.assertIsNone(captured["kwargs"].get("order_by"))
		for field in captured["fields"]:
			self.assertNotIsInstance(field, str)
		self.assertEqual(totals, {"records": 3, "emissions": 10.5, "net": 8.0, "offset": 2.5})

	def test_sum_totals_returns_zeros_when_the_query_is_empty(self):
		class FakeFrappe:
			def get_all(self, *args, **kwargs):
				return []

		original = dashboard._frappe
		dashboard._frappe = lambda: FakeFrappe()
		try:
			totals = dashboard._sum_totals({})
		finally:
			dashboard._frappe = original

		self.assertEqual(totals, {"records": 0, "emissions": 0.0, "net": 0.0, "offset": 0.0})

	def test_period_and_choice_parsers(self):
		self.assertEqual(parse_period(None), 90)
		self.assertEqual(parse_period("30"), 30)
		self.assertEqual(parse_period("0"), 0)
		self.assertEqual(parse_period("12"), 90)
		self.assertEqual(parse_choice("Air Freight", ("Air Freight", "Sea Freight")), "Air Freight")
		self.assertEqual(parse_choice("all", ("Air Freight",)), "")
		self.assertEqual(parse_choice("Nope", ("Air Freight",)), "")
