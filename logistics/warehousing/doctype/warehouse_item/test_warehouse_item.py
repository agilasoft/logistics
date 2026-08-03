# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

import unittest
from unittest.mock import patch

from frappe.tests import IntegrationTestCase

from logistics.warehousing.doctype.warehouse_item.warehouse_item import (
	abbreviate_item_name,
	abbreviate_word,
	build_item_code,
)


EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class TestItemCodeAbbreviation(unittest.TestCase):
	"""Pure unit tests for the compressed Item Name abbreviation algorithm."""

	def test_abbreviate_word_short_words_kept(self):
		self.assertEqual(abbreviate_word("Kit"), "KIT")
		self.assertEqual(abbreviate_word("Oil"), "OIL")
		self.assertEqual(abbreviate_word("A"), "A")
		self.assertEqual(abbreviate_word("ab"), "AB")

	def test_abbreviate_word_long_words(self):
		self.assertEqual(abbreviate_word("Critical"), "CRTC")
		self.assertEqual(abbreviate_word("Spares"), "SPRS")
		self.assertEqual(abbreviate_word("Hydraulic"), "HYDR")
		self.assertEqual(abbreviate_word("Pump"), "PMP")
		self.assertEqual(abbreviate_word("Plastic"), "PLST")
		self.assertEqual(abbreviate_word("Pallet"), "PLLT")
		self.assertEqual(abbreviate_word("Engine"), "ENGN")
		self.assertEqual(abbreviate_word("Filter"), "FLTR")
		self.assertEqual(abbreviate_word("Shipping"), "SHPP")
		self.assertEqual(abbreviate_word("Container"), "CNTN")

	def test_abbreviate_item_name_examples(self):
		self.assertEqual(abbreviate_item_name("Critical Spares Kit"), "CRTC-SPRS-KIT")
		self.assertEqual(abbreviate_item_name("Hydraulic Pump"), "HYDR-PMP")
		self.assertEqual(abbreviate_item_name("Plastic Pallet"), "PLST-PLLT")
		self.assertEqual(abbreviate_item_name("Engine Oil Filter"), "ENGN-OIL-FLTR")
		self.assertEqual(abbreviate_item_name("Shipping Container"), "SHPP-CNTN")

	def test_abbreviate_item_name_strips_stop_words(self):
		self.assertEqual(abbreviate_item_name("Kit of Spares for Engine"), "KIT-SPRS-ENGN")
		self.assertEqual(abbreviate_item_name("A Pallet and a Pump"), "PLLT-PMP")
		self.assertEqual(abbreviate_item_name("Oil & Filter"), "OIL-FLTR")

	def test_build_item_code_prefixes_customer(self):
		self.assertEqual(build_item_code("BEL", "Critical Spares Kit"), "BEL-CRTC-SPRS-KIT")
		self.assertEqual(build_item_code("bel", "Hydraulic Pump"), "BEL-HYDR-PMP")
		self.assertEqual(build_item_code("BEL", "Plastic Pallet"), "BEL-PLST-PLLT")
		self.assertEqual(build_item_code("BEL", "Engine Oil Filter"), "BEL-ENGN-OIL-FLTR")
		self.assertEqual(build_item_code("BEL", "Shipping Container"), "BEL-SHPP-CNTN")

	def test_build_item_code_fallback_when_empty_name(self):
		self.assertEqual(build_item_code("BEL", ""), "BEL-ITEM")
		self.assertEqual(build_item_code("BEL", None), "BEL-ITEM")

	def test_ensure_unique_item_code_appends_numeric_suffix(self):
		import logistics.warehousing.doctype.warehouse_item.warehouse_item as mod

		with patch.object(mod, "frappe") as mock_frappe:
			mock_frappe.db.exists.side_effect = [True, True, False]
			result = mod.ensure_unique_item_code("BEL-CRTC-SPRS-KIT", "Customer-1", None)
		self.assertEqual(result, "BEL-CRTC-SPRS-KIT-3")


class IntegrationTestWarehouseItem(IntegrationTestCase):
	"""
	Integration tests for WarehouseItem.
	Use this class for testing interactions between multiple components.
	"""

	pass
