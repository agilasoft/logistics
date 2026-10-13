# -*- coding: utf-8 -*-
"""Tests for Purchase Invoice BIR 2307 UI hide patch."""

from __future__ import annotations

import sys
import unittest
from unittest.mock import MagicMock, patch

# Patch modules import frappe at load time; stub it for unit tests outside bench.
if "frappe" not in sys.modules:
	sys.modules["frappe"] = MagicMock()

from logistics.patches import v3_0_hide_purchase_invoice_bir_2307_ui_fields as patch_module


class TestHidePurchaseInvoiceBir2307UiFields(unittest.TestCase):
	def test_field_list_covers_bir_section_block(self):
		names = set(patch_module.BIR_2307_UI_FIELDNAMES)
		self.assertIn("bir_2307_section", names)
		self.assertTrue({"payee_tin", "payor_tin"}.issubset(names))

	@patch.object(patch_module.frappe, "clear_cache")
	@patch.object(patch_module.frappe, "make_property_setter")
	@patch.object(patch_module.frappe, "db")
	def test_execute_hides_existing_fields_only(
		self, mock_db, mock_make_property_setter, _mock_clear_cache
	):
		mock_db.exists.side_effect = lambda doctype, name=None, filters=None: (
			True if doctype == "DocType" else False
		)

		meta = MagicMock()

		def get_field(fieldname):
			return fieldname in ("bir_2307_section", "payee_tin")

		meta.get_field.side_effect = get_field
		with patch.object(patch_module.frappe, "get_meta", return_value=meta):
			patch_module.execute()

		self.assertEqual(mock_make_property_setter.call_count, 2)
		hidden_fields = {
			call.args[0]["fieldname"] for call in mock_make_property_setter.call_args_list
		}
		self.assertEqual(hidden_fields, {"bir_2307_section", "payee_tin"})


if __name__ == "__main__":
	unittest.main()
