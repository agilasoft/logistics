# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Job Management sidebar sections follow the workspace groups."""

from __future__ import annotations

import html
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT / "logistics/job_management/workspace/job_management/job_management.json"
SIDEBAR = ROOT / "logistics/job_management/sidebar/job_management/job_management.json"
PATCHES = ROOT / "logistics/patches.txt"
SPRITE = ROOT / "logistics/public/icons/module-icons.svg"

SECTION_ICONS = {
	"Job Operations": "chart-column",
	"Masters": "database",
	"Settings": "settings",
}
REPORT_ICON = "sheet"


def _plain(text):
	return html.unescape(re.sub(r"<[^>]+>", "", text or "")).strip()


def _workspace_outline():
	"""Home, then each workspace group in page order.

	Job Operations shortcuts sit in that section. The Shortcuts header is the
	primary record, so those links stay at the top level. Each card is a section.
	"""
	workspace = json.loads(WORKSPACE.read_text())
	content = json.loads(workspace["content"])
	shortcuts = {row["label"]: row for row in workspace["shortcuts"]}
	cards = {}
	current = None
	for link in workspace["links"]:
		if link.get("type") == "Card Break":
			current = link["label"]
			cards[current] = []
		elif link.get("type") == "Link" and current:
			cards[current].append(link)

	outline = [("link", "Home", "Workspace", "Job Management", "house")]
	mode = None
	for block in content:
		kind = block.get("type")
		data = block.get("data") or {}
		if kind == "header":
			mode = _plain(data.get("text"))
			if mode == "Job Operations":
				outline.append(("section", mode, SECTION_ICONS[mode], 0))
			continue
		if kind == "shortcut" and mode == "Job Operations":
			row = shortcuts[data["shortcut_name"]]
			outline.append(("child", row["label"], "Report", row["link_to"], None))
			continue
		if kind == "shortcut" and mode == "Shortcuts":
			row = shortcuts[data["shortcut_name"]]
			icon = "file-text" if row["type"] == "DocType" else None
			outline.append(("link", row["label"], row["type"], row["link_to"], icon))
			continue
		if kind == "card":
			name = data["card_name"]
			outline.append(("section", name, SECTION_ICONS.get(name, REPORT_ICON), 1))
			for link in cards[name]:
				outline.append(("child", link["label"], link["link_type"], link["link_to"], None))
	return outline


def _sidebar_outline(sidebar):
	outline = []
	for item in sidebar["items"]:
		if item.get("type") == "Section Break":
			outline.append(
				("section", item["label"], item.get("icon"), item.get("keep_closed"))
			)
			continue
		outline.append(
			(
				"child" if item.get("child") else "link",
				item["label"],
				item.get("link_type"),
				item.get("link_to"),
				item.get("icon"),
			)
		)
	return outline


class TestJobManagementSidebarGroups(unittest.TestCase):
	def test_sidebar_follows_workspace_groups(self):
		sidebar = json.loads(SIDEBAR.read_text())
		self.assertEqual(sidebar["doctype"], "Sidebar")
		self.assertEqual(sidebar["name"], "Job Management")
		self.assertEqual(sidebar["title"], "Job Management")
		self.assertEqual(sidebar["module"], "Job Management")
		self.assertEqual(sidebar["app"], "logistics")
		self.assertEqual(sidebar["standard"], 1)
		self.assertEqual(sidebar["header_icon"], "job_management")
		self.assertIn('id="icon-job_management"', SPRITE.read_text())

		items = sidebar["items"]
		self.assertEqual([item["idx"] for item in items], list(range(1, len(items) + 1)))
		self.assertEqual(_sidebar_outline(sidebar), _workspace_outline())

		open_sections = [
			item["label"]
			for item in items
			if item.get("type") == "Section Break" and not item.get("keep_closed")
		]
		self.assertEqual(open_sections, ["Job Operations"])
		for item in items:
			if item.get("type") == "Section Break":
				self.assertEqual(item["child"], 0)
				self.assertEqual(item["indent"], 1)
			elif item.get("child"):
				self.assertEqual(item["indent"], 0)

	def test_migrate_refreshes_the_sidebar(self):
		text = PATCHES.read_text()
		self.assertIn("logistics.patches.v3_0_sync_job_management_sidebar", text)
		patch = (ROOT / "logistics/patches/v3_0_sync_job_management_sidebar.py").read_text()
		self.assertIn('"job_management.json"', patch)
		self.assertIn('"sidebar"', patch)
		self.assertIn('SIDEBAR_NAME = "Job Management"', patch)
