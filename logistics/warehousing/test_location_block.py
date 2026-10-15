# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""A multi-position handling unit must land on consecutive location codes."""

from __future__ import annotations

import unittest

from logistics.warehousing.location_block import (
	list_contiguous_location_blocks,
	location_code_number,
)


def _loc(name, aisle, bay, level, code, site="ATN", building="DIMI", zone="MAIN"):
	return {
		"location": name,
		"site": site,
		"building": building,
		"zone": zone,
		"aisle": aisle,
		"bay": bay,
		"level": level,
		"location_code": code,
	}


class TestLocationCodeNumber(unittest.TestCase):
	def test_plain_and_padded_codes_are_the_same_position(self):
		self.assertEqual(location_code_number("4"), 4)
		self.assertEqual(location_code_number("04"), 4)
		self.assertEqual(location_code_number(4), 4)
		self.assertEqual(location_code_number(" 01 "), 1)

	def test_blank_and_words_are_not_positions(self):
		self.assertIsNone(location_code_number(None))
		self.assertIsNone(location_code_number(""))
		self.assertIsNone(location_code_number("A"))
		self.assertIsNone(location_code_number("1A"))


class TestContiguousLocationBlocks(unittest.TestCase):
	def test_four_positions_stay_on_one_aisle_bay_and_level(self):
		locations = [
			_loc("far-b", "Aisle-B", "Bay-14", "Level-1", "1"),
			_loc("far-c", "Aisle-C", "Bay-02", "Level-3", "1"),
			_loc("p1", "Aisle-A", "Bay-02", "Level-1", "1"),
			_loc("p2", "Aisle-A", "Bay-02", "Level-1", "2"),
			_loc("p3", "Aisle-A", "Bay-02", "Level-1", "3"),
			_loc("p4", "Aisle-A", "Bay-02", "Level-1", "4"),
		]
		blocks = list_contiguous_location_blocks(locations, 4)
		self.assertEqual(blocks[0], ["p1", "p2", "p3", "p4"])

	def test_padded_codes_line_up_in_code_order(self):
		locations = [
			_loc("p4", "Aisle-A", "Bay-02", "Level-1", "04"),
			_loc("p2", "Aisle-A", "Bay-02", "Level-1", "02"),
			_loc("p1", "Aisle-A", "Bay-02", "Level-1", "01"),
			_loc("p3", "Aisle-A", "Bay-02", "Level-1", "03"),
		]
		blocks = list_contiguous_location_blocks(locations, 4)
		self.assertEqual(blocks[0], ["p1", "p2", "p3", "p4"])

	def test_a_gap_in_the_codes_is_not_a_block(self):
		locations = [
			_loc("p1", "Aisle-A", "Bay-02", "Level-1", "1"),
			_loc("p2", "Aisle-A", "Bay-02", "Level-1", "2"),
			_loc("p4", "Aisle-A", "Bay-02", "Level-1", "4"),
			_loc("p5", "Aisle-A", "Bay-02", "Level-1", "5"),
		]
		self.assertEqual(list_contiguous_location_blocks(locations, 4), [])

	def test_positions_on_another_level_or_bay_stay_separate(self):
		locations = [
			_loc("a1", "Aisle-A", "Bay-02", "Level-1", "1"),
			_loc("a2", "Aisle-A", "Bay-02", "Level-1", "2"),
			_loc("b1", "Aisle-A", "Bay-02", "Level-2", "3"),
			_loc("b2", "Aisle-A", "Bay-02", "Level-2", "4"),
			_loc("c1", "Aisle-A", "Bay-03", "Level-1", "3"),
			_loc("c2", "Aisle-A", "Bay-03", "Level-1", "4"),
		]
		self.assertEqual(list_contiguous_location_blocks(locations, 4), [])

	def test_the_same_aisle_name_in_another_site_is_a_different_place(self):
		locations = [
			_loc("s1", "Aisle-A", "Bay-02", "Level-1", "1", site="ATN"),
			_loc("s2", "Aisle-A", "Bay-02", "Level-1", "2", site="ATN"),
			_loc("s3", "Aisle-A", "Bay-02", "Level-1", "3", site="OTHER"),
			_loc("s4", "Aisle-A", "Bay-02", "Level-1", "4", site="OTHER"),
		]
		self.assertEqual(list_contiguous_location_blocks(locations, 4), [])

	def test_the_preferred_complete_block_is_chosen(self):
		preferred = [
			_loc(f"pref-{code}", "Aisle-A", "Bay-09", "Level-1", str(code))
			for code in (1, 2, 3, 4)
		]
		later = [
			_loc(f"later-{code}", "Aisle-A", "Bay-02", "Level-1", str(code))
			for code in (1, 2, 3, 4)
		]
		blocks = list_contiguous_location_blocks(preferred + later, 4)
		self.assertEqual(blocks[0], ["pref-1", "pref-2", "pref-3", "pref-4"])

	def test_lowest_location_codes_in_the_bay_are_used_first(self):
		high = [
			_loc(f"high-{code}", "Aisle-A", "Bay-02", "Level-1", str(code))
			for code in (5, 6, 7, 8)
		]
		low = [
			_loc(f"low-{code}", "Aisle-A", "Bay-02", "Level-1", str(code))
			for code in (1, 2, 3, 4)
		]
		blocks = list_contiguous_location_blocks(high + low, 4)
		self.assertEqual(blocks[0], ["low-1", "low-2", "low-3", "low-4"])

	def test_the_row_starts_at_the_lowest_free_code(self):
		locations = [
			_loc(f"p-{code}", "Aisle-A", "Bay-02", "Level-1", str(code))
			for code in (2, 3, 4, 5, 6, 7, 8)
		]
		blocks = list_contiguous_location_blocks(locations, 4)
		self.assertEqual(blocks[0], ["p-2", "p-3", "p-4", "p-5"])

	def test_one_position_is_not_a_block(self):
		locations = [_loc("only", "Aisle-A", "Bay-02", "Level-1", "1")]
		self.assertEqual(list_contiguous_location_blocks(locations, 1), [])


if __name__ == "__main__":
	unittest.main()
