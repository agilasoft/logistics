# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Every logistics module workspace and sidebar opens Workflow Center."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from logistics.workflow_center.desk_links import (
	ACCESS_HEADERS,
	ICON,
	LABEL,
	PAGE,
	apply_sidebar,
	apply_workspace,
	_header_text,
)


ROOT = Path(__file__).resolve().parents[3]
PAGE_PATH = ROOT / "logistics/logistics/page/workflow_center/workflow_center.json"
PATCHES = ROOT / "logistics/patches.txt"


def _load(path: Path) -> dict:
	return json.loads(path.read_text())


def _shortcut_names(workspace: dict) -> list[str]:
	blocks = json.loads(workspace["content"])
	return [
		(block.get("data") or {}).get("shortcut_name")
		for block in blocks
		if block.get("type") == "shortcut"
	]


class TestWorkflowCenterModuleLinks(unittest.TestCase):
	def test_page_is_shipped_with_logistics(self):
		page = _load(PAGE_PATH)
		self.assertEqual(page["name"], PAGE)
		self.assertEqual(page["page_name"], PAGE)
		self.assertEqual(page["title"], LABEL)
		self.assertEqual(page["module"], "Logistics")
		self.assertEqual(page["standard"], "Yes")

	def test_migrate_adds_the_links(self):
		text = PATCHES.read_text()
		self.assertIn("logistics.patches.v3_0_add_workflow_center_to_module_workspaces", text)

	def test_each_workspace_shortcut_opens_the_page(self):
		paths = sorted((ROOT / "logistics").glob("**/workspace/**/*.json"))
		self.assertGreaterEqual(len(paths), 15)
		for path in paths:
			workspace = _load(path)
			row = next(item for item in workspace["shortcuts"] if item["label"] == LABEL)
			self.assertEqual(row["type"], "Page", path)
			self.assertEqual(row["link_to"], PAGE, path)
			names = _shortcut_names(workspace)
			self.assertIn(LABEL, names, path)
			self.assertEqual(names.count(LABEL), 1, path)
			if "Control Tower" in names:
				self.assertEqual(names[names.index("Control Tower") + 1], LABEL, path)
			else:
				self.assertEqual(_first_access_shortcut(workspace), LABEL, path)
			again = json.loads(json.dumps(workspace))
			self.assertFalse(apply_workspace(again), path)

	def test_each_sidebar_link_sits_with_control_tower(self):
		paths = sorted((ROOT / "logistics").glob("**/sidebar/**/*.json"))
		self.assertGreaterEqual(len(paths), 10)
		for path in paths:
			sidebar = _load(path)
			items = sidebar["items"]
			self.assertEqual([item["idx"] for item in items], list(range(1, len(items) + 1)), path)
			labels = [item["label"] for item in items]
			index = labels.index(LABEL)
			link = items[index]
			self.assertEqual(link["type"], "Link", path)
			self.assertEqual(link["link_type"], "Page", path)
			self.assertEqual(link["link_to"], PAGE, path)
			self.assertEqual(link["icon"], ICON, path)
			self.assertEqual(link["child"], 0, path)
			if "Control Tower" in labels:
				self.assertEqual(labels[labels.index("Control Tower") + 1], LABEL, path)
			else:
				self.assertEqual(labels[labels.index("Home") + 1], LABEL, path)
			again = json.loads(json.dumps(sidebar))
			self.assertFalse(apply_sidebar(again), path)

	def test_insert_places_the_link_after_control_tower(self):
		workspace = {
			"content": json.dumps(
				[
					{"id": "h", "type": "header", "data": {"text": "<span>Quick Access</span>", "col": 12}},
					{"id": "ct", "type": "shortcut", "data": {"shortcut_name": "Control Tower", "col": 3}},
					{"id": "sq", "type": "shortcut", "data": {"shortcut_name": "Sales Quote", "col": 3}},
				],
				separators=(",", ":"),
			),
			"shortcuts": [
				{"label": "Control Tower", "link_to": "Sea Freight Control Tower", "type": "Dashboard"},
				{"label": "Sales Quote", "link_to": "Sales Quote", "type": "DocType"},
			],
		}
		self.assertTrue(apply_workspace(workspace))
		self.assertEqual(
			[row["label"] for row in workspace["shortcuts"][:2]],
			["Control Tower", LABEL],
		)
		self.assertEqual(workspace["shortcuts"][1]["link_to"], PAGE)
		self.assertFalse(apply_workspace(workspace))

		sidebar = {
			"items": [
				{"idx": 1, "label": "Home", "type": "Link", "icon": "house", "child": 0},
				{"idx": 2, "label": "Control Tower", "type": "Link", "icon": "tower-control", "child": 0},
				{"idx": 3, "label": "Sales Quote", "type": "Link", "icon": "file-pen-line", "child": 0},
			]
		}
		self.assertTrue(apply_sidebar(sidebar))
		self.assertEqual([item["label"] for item in sidebar["items"][:3]], ["Home", "Control Tower", LABEL])
		self.assertEqual([item["idx"] for item in sidebar["items"]], [1, 2, 3, 4])
		self.assertFalse(apply_sidebar(sidebar))


def _first_access_shortcut(workspace: dict) -> str:
	blocks = json.loads(workspace["content"])
	access_at = None
	for index, block in enumerate(blocks):
		if block.get("type") == "header" and _header_text(block) in ACCESS_HEADERS:
			access_at = index
			break
	start = 0 if access_at is None else access_at + 1
	if access_at is None:
		for index, block in enumerate(blocks):
			if block.get("type") == "header":
				start = index + 1
				break
	for block in blocks[start:]:
		if block.get("type") == "header" and access_at is not None:
			break
		if block.get("type") == "shortcut":
			return (block.get("data") or {}).get("shortcut_name")
	return ""


if __name__ == "__main__":
	unittest.main()
