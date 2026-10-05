# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""The programme dock tile is MICE."""

from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

from logistics.mice.desk_icon import relabel_desk_layout


ROOT = Path(__file__).resolve().parents[2]


class TestMiceDeskIcon(unittest.TestCase):
	def test_shipped_tile_is_named_mice(self):
		icon = json.loads((ROOT / "logistics/desktop_icon/mice.json").read_text())
		sidebar = json.loads((ROOT / "logistics/workspace_sidebar/mice.json").read_text())
		workspace = json.loads((ROOT / "logistics/mice/workspace/mice/mice.json").read_text())
		self.assertEqual(icon["label"], "MICE")
		self.assertEqual(icon["link_to"], "MICE")
		self.assertEqual(sidebar["title"], "MICE")
		self.assertEqual(workspace["title"], "MICE")
		self.assertFalse((ROOT / "logistics/desktop_icon/exhibits.json").exists())
		self.assertFalse((ROOT / "logistics/workspace_sidebar/exhibits.json").exists())
		self.assertFalse((ROOT / "logistics/exhibits/workspace/exhibits/exhibits.json").exists())

	def test_exhibits_module_is_not_its_own_dock_entry(self):
		hooks = ast.parse((ROOT / "logistics/hooks.py").read_text())
		mapping = None
		for node in hooks.body:
			if isinstance(node, ast.Assign) and any(
				isinstance(target, ast.Name) and target.id == "code_only_modules" for target in node.targets
			):
				mapping = ast.literal_eval(node.value)
		self.assertEqual(mapping, {"Exhibits": ["MICE"]})

	def test_saved_layout_keeps_one_mice_tile(self):
		layout = relabel_desk_layout(
			[
				{"label": "Transport", "link_to": "Transport"},
				{"label": "Exhibits", "link_to": "Exhibits", "name": "Exhibits"},
				{"label": "MICE", "link_to": "MICE"},
			]
		)
		self.assertEqual([icon["label"] for icon in layout], ["Transport", "MICE"])

	def test_saved_layout_renames_a_lone_exhibits_tile(self):
		layout = relabel_desk_layout([{"label": "Exhibits", "link_to": "Exhibits", "name": "Exhibits"}])
		self.assertEqual(layout, [{"label": "MICE", "link_to": "MICE", "name": "MICE"}])


if __name__ == "__main__":
	unittest.main()
