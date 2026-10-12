# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Time Sensitive sidebar follows the same desk pattern as the other modules."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SIDEBAR = ROOT / "logistics/time_sensitive/sidebar/time_sensitive/time_sensitive.json"
WORKSPACE = ROOT / "logistics/time_sensitive/workspace/time_sensitive/time_sensitive.json"
PATCHES = ROOT / "logistics/patches.txt"
SPRITE = ROOT / "logistics/public/icons/module-icons.svg"

PINNED = (
	("Home", "Workspace", "Time Sensitive", "house"),
	("Control Tower", "Dashboard", "Time Sensitive Control Tower", "tower-control"),
	("Workflow Center", "Page", "workflow-center", "workflow"),
	("Time Sensitive Case", "DocType", "Time Sensitive Case", "timer"),
	("Sales Quote", "DocType", "Sales Quote", "file-pen-line"),
)

SECTION_ICONS = {
	"Operations": "chart-column",
	"Setup": "settings",
	"Service Modes": "route",
}

QUEUE_FILTERS = {
	"Ongoing": [["Time Sensitive Case", "status", "in", ["Activated", "In Execution", "On Hold"]]],
	"Nearing Due": [["Time Sensitive Case", "sla_status", "=", "At Risk"]],
	"Overdue": [["Time Sensitive Case", "sla_status", "=", "Breached"]],
}


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


class TestTimeSensitiveSidebar(unittest.TestCase):
	def test_sidebar_matches_other_modules(self):
		sidebar = json.loads(SIDEBAR.read_text())
		self.assertEqual(sidebar["doctype"], "Sidebar")
		self.assertEqual(sidebar["name"], "Time Sensitive")
		self.assertEqual(sidebar["title"], "Time Sensitive")
		self.assertEqual(sidebar["module"], "Time Sensitive")
		self.assertEqual(sidebar["app"], "logistics")
		self.assertEqual(sidebar["standard"], 1)
		self.assertEqual(sidebar["header_icon"], "time_sensitive")
		self.assertIn('id="icon-time_sensitive"', SPRITE.read_text())

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
			self.assertEqual(item["icon"], SECTION_ICONS[item["label"]])
		open_sections = [item["label"] for item in sections if not item.get("keep_closed")]
		self.assertEqual(open_sections, [])

		groups = {}
		current = None
		for item in items:
			if item.get("type") == "Section Break":
				current = item["label"]
				groups[current] = []
			elif current and item.get("child"):
				self.assertEqual(item["indent"], 0)
				self.assertFalse(item.get("icon"))
				groups[current].append(item["label"])

		cards = _workspace_cards()
		promoted = {"Time Sensitive Case", "Sales Quote"}
		self.assertEqual(
			groups["Operations"],
			list(QUEUE_FILTERS) + [label for label in cards["Operations"] if label not in promoted],
		)
		self.assertEqual(groups["Setup"], cards["Setup"])
		self.assertEqual(groups["Service Modes"], cards["Service Modes"])

		for item in items:
			if item["label"] in QUEUE_FILTERS:
				self.assertEqual(item["link_to"], "Time Sensitive Case")
				self.assertEqual(item["link_type"], "DocType")
				self.assertEqual(json.loads(item["filters"]), QUEUE_FILTERS[item["label"]])
			elif item.get("type") == "Link" and item["label"] not in QUEUE_FILTERS:
				self.assertFalse(item.get("filters"))

	def test_migrate_refreshes_the_sidebar(self):
		text = PATCHES.read_text()
		self.assertIn("logistics.patches.v3_0_sync_time_sensitive_sidebar", text)
		patch = (ROOT / "logistics/patches/v3_0_sync_time_sensitive_sidebar.py").read_text()
		self.assertIn('"time_sensitive.json"', patch)
		self.assertIn('"sidebar"', patch)
		self.assertIn('SIDEBAR_NAME = "Time Sensitive"', patch)
