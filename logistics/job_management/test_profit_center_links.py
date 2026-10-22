# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt
"""Profit Center link fields only offer active records."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from logistics.job_management.profit_center_links import (
	active_profit_center_link_filters,
	allows_inactive_profit_centers,
	keep_active_profit_center_rows,
	merge_active_link_filters,
)

APP_ROOT = Path(__file__).resolve().parents[1]


def _link_fields(document):
	doctype = document.get("doctype")
	if doctype == "DocType":
		for field in document.get("fields") or []:
			if isinstance(field, dict):
				yield field
	elif isinstance(document.get("custom_fields"), list):
		for field in document["custom_fields"]:
			if isinstance(field, dict):
				yield field


def _profit_center_links(document):
	for field in _link_fields(document):
		if field.get("fieldtype") == "Link" and field.get("options") == "Profit Center":
			yield field


class TestProfitCenterLinkFilters(unittest.TestCase):
	def test_merge_appends_active_filter(self):
		merged = merge_active_link_filters(
			'[["Profit Center", "company", "=", "eval:doc.company"]]'
		)
		rows = json.loads(merged)
		self.assertEqual(rows[-1], ["Profit Center", "is_active", "=", 1])
		self.assertEqual(rows[0][1], "company")

	def test_merge_leaves_existing_active_filter(self):
		raw = '[["Profit Center", "is_active", "=", 1]]'
		self.assertIsNone(merge_active_link_filters(raw))

	def test_merge_from_empty(self):
		expected = [["Profit Center", "is_active", "=", 1]]
		self.assertEqual(json.loads(merge_active_link_filters(None)), expected)
		self.assertEqual(json.loads(merge_active_link_filters("")), expected)
		self.assertEqual(json.loads(merge_active_link_filters("null")), expected)

	def test_search_filters_default_to_active(self):
		self.assertEqual(active_profit_center_link_filters(None), {"is_active": 1})
		self.assertEqual(
			active_profit_center_link_filters({"company": "Acme"}),
			{"company": "Acme", "is_active": 1},
		)
		self.assertEqual(
			active_profit_center_link_filters([["Profit Center", "company", "=", "Acme"]]),
			[
				["Profit Center", "company", "=", "Acme"],
				["Profit Center", "is_active", "=", 1],
			],
		)

	def test_search_filters_keep_an_explicit_choice(self):
		self.assertEqual(active_profit_center_link_filters({"is_active": 0}), {"is_active": 0})
		self.assertEqual(
			active_profit_center_link_filters({"include_disabled": 1, "company": "Acme"}),
			{"include_disabled": 1, "company": "Acme"},
		)
		self.assertTrue(allows_inactive_profit_centers({"include_disabled": 1}))
		self.assertTrue(allows_inactive_profit_centers([["is_active", "!=", 1]]))
		self.assertFalse(allows_inactive_profit_centers(None))
		self.assertFalse(allows_inactive_profit_centers({"is_active": 1}))

	def test_result_rows_drop_inactive_names(self):
		rows = [("ACTIVE", "Active"), ("OLD", "Old")]
		self.assertEqual(
			keep_active_profit_center_rows(rows, active_names={"ACTIVE"}),
			[("ACTIVE", "Active")],
		)
		self.assertEqual(
			keep_active_profit_center_rows([{"name": "OLD"}], active_names=set()),
			[],
		)
		self.assertEqual(
			keep_active_profit_center_rows([{"name": "ACTIVE"}, {"value": "OLD"}], active_names={"ACTIVE"}),
			[{"name": "ACTIVE"}],
		)

	def test_doctype_and_custom_links_require_active(self):
		missing = []
		found = 0
		for path in APP_ROOT.rglob("*.json"):
			try:
				document = json.loads(path.read_text())
			except (OSError, json.JSONDecodeError):
				continue
			if not isinstance(document, dict):
				continue
			if document.get("doctype") not in ("DocType", None) and "custom_fields" not in document:
				continue
			if document.get("doctype") == "Web Form" or document.get("doctype") == "Report":
				continue
			for field in _profit_center_links(document):
				found += 1
				filters = field.get("link_filters") or ""
				if "is_active" not in filters:
					missing.append(f"{path.relative_to(APP_ROOT)}:{field.get('fieldname')}")
		self.assertGreater(found, 0)
		self.assertEqual(missing, [])
