# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Sales Quote keeps a typed scope title and fills a blank one from the corridor."""

from __future__ import annotations

import unittest

from logistics.pricing_center.sales_quote_scope_title import default_scope_title


class TestScopeTitle(unittest.TestCase):
	def test_existing_title_is_kept(self):
		self.assertEqual(
			default_scope_title("Manila lane", "MNL", "SIN", None, None, "FOB"),
			"Manila lane",
		)

	def test_ports_and_incoterm_fill_a_blank_title(self):
		self.assertEqual(
			default_scope_title("  ", "MNL", "SIN", "Door A", "Door B", "FOB"),
			"MNL → SIN (FOB)",
		)

	def test_locations_are_used_when_a_port_is_missing(self):
		self.assertEqual(
			default_scope_title(None, "MNL", None, "Door A", "Door B", None),
			"Door A → Door B",
		)

	def test_incoterm_alone_is_enough(self):
		self.assertEqual(default_scope_title(None, None, None, None, None, " CIF "), "(CIF)")

	def test_blank_corridor_leaves_the_title_unchanged(self):
		self.assertIsNone(default_scope_title(None, "  ", None, None, "Door B", "  "))
		self.assertEqual(default_scope_title("   ", None, None, None, None, None), "   ")


if __name__ == "__main__":
	unittest.main()
