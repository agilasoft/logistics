# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Retired transport DocTypes stay out of the desk and are dropped only when empty."""

from __future__ import annotations

import unittest
from pathlib import Path

from logistics.patches.v3_0_drop_empty_proof_of_delivery_and_plate_coding_rule import (
	PLATE_CODING_DIGITS,
	PLATE_CODING_RULE,
	PROOF_OF_DELIVERY,
	doctypes_to_drop,
)


PACKAGE = Path(__file__).resolve().parents[1]

REMOVED = (
	"transport/doctype/proof_of_delivery",
	"transport/doctype/plate_coding_rule",
	"transport/doctype/plate_coding_restricted_digits",
)

KEPT = (
	"transport/doctype/odds_order/odds_order.py",
	"transport/print_format/proof_of_delivery/install_print_format.py",
	"exhibits/doctype/exhibit/exhibit.py",
	"mice/doctype/mice_project/mice_project.py",
)


class TestRetiredTransportDoctypes(unittest.TestCase):
	def test_empty_tables_drop_child_before_parent(self):
		self.assertEqual(
			doctypes_to_drop({}),
			[PROOF_OF_DELIVERY, PLATE_CODING_DIGITS, PLATE_CODING_RULE],
		)

	def test_existing_rows_keep_the_doctype(self):
		self.assertNotIn(PROOF_OF_DELIVERY, doctypes_to_drop({PROOF_OF_DELIVERY: 2}))
		kept = doctypes_to_drop({PLATE_CODING_RULE: 1})
		self.assertNotIn(PLATE_CODING_RULE, kept)
		self.assertNotIn(PLATE_CODING_DIGITS, kept)
		kept_child = doctypes_to_drop({PLATE_CODING_DIGITS: 1})
		self.assertNotIn(PLATE_CODING_RULE, kept_child)
		self.assertNotIn(PLATE_CODING_DIGITS, kept_child)

	def test_files_and_menu_match_the_recommendation(self):
		for relative in REMOVED:
			self.assertFalse((PACKAGE / relative).exists(), relative)
		for relative in KEPT:
			self.assertTrue((PACKAGE / relative).is_file(), relative)
		for config in (
			PACKAGE / "config" / "transport.py",
			PACKAGE / "transport" / "config" / "transport.py",
		):
			self.assertNotIn("Proof of Delivery", config.read_text())
		patches = (PACKAGE / "patches.txt").read_text()
		self.assertIn(
			"logistics.patches.v3_0_drop_empty_proof_of_delivery_and_plate_coding_rule",
			patches,
		)


if __name__ == "__main__":
	unittest.main()
