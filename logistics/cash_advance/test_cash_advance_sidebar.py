# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Cash Advance sidebar follows the same desk pattern as the other modules."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SIDEBAR = ROOT / "logistics/cash_advance/sidebar/cash_advance/cash_advance.json"
WORKSPACE = ROOT / "logistics/cash_advance/workspace/cash_advance/cash_advance.json"
PATCHES = ROOT / "logistics/patches.txt"
SPRITE = ROOT / "logistics/public/icons/module-icons.svg"
REPORTS = ROOT / "logistics/cash_advance/report"
DOCTYPES = ROOT / "logistics/cash_advance/doctype"

PINNED = (
	("Home", "Workspace", "Cash Advance", "house"),
	("Dashboard", "Dashboard", "Cash Advance", "chart-column"),
	("Workflow Center", "Page", "workflow-center", "workflow"),
	("Cash Advance Request", "DocType", "Cash Advance Request", "wallet"),
	("Cash Advance Liquidation", "DocType", "Cash Advance Liquidation", "receipt"),
	("Cash Acknowledgment", "DocType", "Cash Acknowledgment", "file-check-corner"),
)

SECTION_ICONS = {
	"Setup": "settings",
	"Aging & Overdue": "sheet",
	"Pipeline & Trends": "sheet",
	"Concentration & Workload": "sheet",
}

SETUP = ("Cash Advance Settings", "Cash Advance Reason Code")


def _workspace_cards():
	workspace = json.loads(WORKSPACE.read_text())
	cards = {}
	current = None
	for link in workspace["links"]:
		if link.get("type") == "Card Break":
			current = link["label"]
			cards[current] = []
		elif current and link.get("type") == "Link":
			cards[current].append(link["label"])
	return cards


def _parent_doctypes():
	names = []
	for path in DOCTYPES.glob("*/*.json"):
		data = json.loads(path.read_text())
		if data.get("doctype") == "DocType" and not data.get("istable"):
			names.append(data["name"])
	return names


def _report_names():
	names = []
	for path in REPORTS.glob("*/*.json"):
		data = json.loads(path.read_text())
		if data.get("doctype") == "Report":
			names.append(data["name"])
	return names


class TestCashAdvanceSidebar(unittest.TestCase):
	def test_sidebar_matches_other_modules(self):
		sidebar = json.loads(SIDEBAR.read_text())
		self.assertEqual(sidebar["doctype"], "Sidebar")
		self.assertEqual(sidebar["name"], "Cash Advance")
		self.assertEqual(sidebar["title"], "Cash Advance")
		self.assertEqual(sidebar["module"], "Cash Advance")
		self.assertEqual(sidebar["app"], "logistics")
		self.assertEqual(sidebar["standard"], 1)
		self.assertEqual(sidebar["header_icon"], "cash_advance")
		self.assertIn('id="icon-cash_advance"', SPRITE.read_text())

		items = sidebar["items"]
		self.assertEqual([item["idx"] for item in items], list(range(1, len(items) + 1)))

		pinned = [
			(item["label"], item["link_type"], item["link_to"], item["icon"])
			for item in items
			if item.get("type") == "Link" and not item.get("child")
		]
		self.assertEqual(pinned, list(PINNED))

		sections = [item for item in items if item.get("type") == "Section Break"]
		self.assertEqual([item["label"] for item in sections], list(SECTION_ICONS))
		for item in sections:
			self.assertEqual(item["child"], 0)
			self.assertEqual(item["indent"], 1)
			self.assertEqual(item["collapsible"], 1)
			self.assertEqual(item["keep_closed"], 1)
			self.assertEqual(item["icon"], SECTION_ICONS[item["label"]])

		groups = {}
		current = None
		for item in items:
			if item.get("type") == "Section Break":
				current = item["label"]
				groups[current] = []
			elif current and item.get("child"):
				self.assertEqual(item["indent"], 0)
				self.assertFalse(item.get("icon"))
				self.assertEqual(item["type"], "Link")
				self.assertFalse(item.get("filters"))
				groups[current].append((item["label"], item["link_type"], item["link_to"]))

		self.assertEqual([row[0] for row in groups["Setup"]], list(SETUP))
		for label, link_type, link_to in groups["Setup"]:
			self.assertEqual(link_type, "DocType")
			self.assertEqual(link_to, label)

		cards = _workspace_cards()
		self.assertEqual(list(cards), ["Aging & Overdue", "Pipeline & Trends", "Concentration & Workload"])
		for name, links in cards.items():
			self.assertEqual(
				[(label, link_type, link_to) for label, link_type, link_to in groups[name]],
				[(label, "Report", label) for label in links],
			)

		sidebar_reports = [
			link_to
			for rows in groups.values()
			for _label, link_type, link_to in rows
			if link_type == "Report"
		]
		self.assertCountEqual(sidebar_reports, _report_names())
		self.assertEqual(len(sidebar_reports), len(set(sidebar_reports)))

		sidebar_doctypes = [
			item["link_to"]
			for item in items
			if item.get("type") == "Link" and item.get("link_type") == "DocType"
		]
		self.assertCountEqual(sidebar_doctypes, _parent_doctypes())

	def test_migrate_refreshes_the_sidebar(self):
		text = PATCHES.read_text()
		self.assertIn("logistics.patches.v3_0_sync_cash_advance_sidebar", text)
		patch = (ROOT / "logistics/patches/v3_0_sync_cash_advance_sidebar.py").read_text()
		self.assertIn('"cash_advance.json"', patch)
		self.assertIn('"sidebar"', patch)
		self.assertIn('SIDEBAR_NAME = "Cash Advance"', patch)
