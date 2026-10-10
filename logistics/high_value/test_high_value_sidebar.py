# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""High Value sidebar follows the workspace groups shown on the Home page."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SIDEBAR_PATH = ROOT / "logistics/high_value/sidebar/high_value/high_value.json"
WORKSPACE_PATH = ROOT / "logistics/high_value/workspace/high_value/high_value.json"


def _header_label(html: str) -> str:
	match = re.search(r"<b>(.*?)</b>", html or "")
	return match.group(1) if match else ""


def _workspace_groups(workspace: dict) -> list[dict]:
	"""Page order: a header of shortcuts is one section; cards are their own sections."""
	cards: dict[str, list[dict]] = {}
	current = None
	for row in workspace["links"]:
		if row.get("type") == "Card Break":
			current = row["label"]
			cards[current] = []
		elif current and row.get("type") == "Link":
			cards[current].append(
				{
					"label": row["label"],
					"link_to": row["link_to"],
					"link_type": row["link_type"],
				}
			)

	shortcuts = {row["label"]: row for row in workspace["shortcuts"]}
	headers: list[dict] = []
	header = None
	for block in json.loads(workspace["content"]):
		kind = block.get("type")
		data = block.get("data") or {}
		if kind == "header":
			header = {"name": _header_label(data.get("text")), "shortcuts": [], "cards": []}
			headers.append(header)
		elif kind == "shortcut" and header is not None:
			if data.get("shortcut_name") in ("Control Tower", "Workflow Center"):
				continue
			header["shortcuts"].append(shortcuts[data["shortcut_name"]])
		elif kind == "card" and header is not None:
			header["cards"].append(data["card_name"])

	expected: list[dict] = [
		{
			"type": "Link",
			"child": 0,
			"label": "Home",
			"link_to": workspace["name"],
			"link_type": "Workspace",
		}
	]
	for name in ("Control Tower", "Workflow Center"):
		pinned = shortcuts.get(name)
		if pinned:
			expected.append(_shortcut_item(pinned, child=0))
	for group in headers:
		if group["cards"]:
			for shortcut in group["shortcuts"]:
				expected.append(_shortcut_item(shortcut, child=0))
			for card_name in group["cards"]:
				expected.append({"type": "Section Break", "child": 0, "label": card_name})
				expected.extend(
					{**link, "type": "Link", "child": 1} for link in cards[card_name]
				)
			continue
		expected.append({"type": "Section Break", "child": 0, "label": group["name"]})
		expected.extend(_shortcut_item(shortcut, child=1) for shortcut in group["shortcuts"])
	return expected


def _shortcut_item(shortcut: dict, *, child: int) -> dict:
	item = {
		"type": "Link",
		"child": child,
		"label": shortcut["label"],
		"link_to": shortcut["link_to"],
		"link_type": shortcut["type"],
	}
	filters = json.loads(shortcut.get("stats_filter") or "[]")
	if filters:
		item["filters"] = filters
	return item


def _sidebar_item(row: dict) -> dict:
	item = {
		"type": row["type"],
		"child": row["child"],
		"label": row["label"],
	}
	if row["type"] == "Link":
		item["link_to"] = row["link_to"]
		item["link_type"] = row["link_type"]
		if row.get("filters"):
			item["filters"] = json.loads(row["filters"])
	return item


class TestHighValueSidebarGroups(unittest.TestCase):
	def test_sidebar_follows_workspace_groups(self):
		sidebar = json.loads(SIDEBAR_PATH.read_text())
		workspace = json.loads(WORKSPACE_PATH.read_text())
		actual = [_sidebar_item(row) for row in sidebar["items"]]
		expected = _workspace_groups(workspace)
		self.assertEqual(actual, expected)

	def test_sections_are_collapsible_and_indexed(self):
		sidebar = json.loads(SIDEBAR_PATH.read_text())
		self.assertEqual(sidebar["name"], "High Value")
		self.assertEqual(sidebar["module"], "High Value")
		items = sidebar["items"]
		self.assertEqual([row["idx"] for row in items], list(range(1, len(items) + 1)))
		open_section = None
		for row in items:
			if row["type"] == "Section Break":
				self.assertEqual(row["child"], 0)
				self.assertEqual(row["collapsible"], 1)
				self.assertTrue(row.get("icon"))
				open_section = row["label"]
			elif row["child"]:
				self.assertIsNotNone(open_section)
				self.assertEqual(row["type"], "Link")
				self.assertTrue(row.get("link_to"))
			else:
				open_section = None
				self.assertTrue(row.get("icon"))
