# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""The Customs desktop tile opens the desk, not the old /app prefix."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from logistics.customs.desktop_icon_route import (
	DESK_ROUTE,
	apply_desk_route,
	apply_desk_route_to_doc,
	is_customs_tile,
	walk_icons,
)


ROOT = Path(__file__).resolve().parents[3]
ICON_PATH = ROOT / "logistics/desktop_icon/customs.json"
SIDEBAR_PATH = ROOT / "logistics/customs/sidebar/customs/customs.json"
PATCHES_PATH = ROOT / "logistics/patches.txt"


def _load(path: Path) -> dict:
	return json.loads(path.read_text())


def _grid_href(icon: dict) -> str | None:
	"""The path Frappe's desktop ``get_route()`` would put on this tile.

	An External link is copied verbatim. A Workspace Sidebar tile with no
	``sidebar`` value opens the module home. Customs' home is the workspace,
	which the desk addresses as ``/desk/customs``.
	"""
	if icon.get("sidebar"):
		return None
	if icon.get("link_type") == "External" and icon.get("link"):
		return icon["link"]
	if icon.get("link_type") == "Workspace Sidebar" and icon.get("link_to") == "Customs":
		return "/desk/customs"
	return None


class TestCustomsDesktopIcon(unittest.TestCase):
	def test_shipped_tile_opens_the_desk_workspace(self):
		icon = _load(ICON_PATH)
		sidebar = _load(SIDEBAR_PATH)
		home = sidebar["items"][0]
		self.assertEqual(icon["label"], "Customs")
		self.assertEqual(icon["name"], "Customs")
		self.assertEqual(icon["link_type"], "Workspace Sidebar")
		self.assertEqual(icon["link_to"], "Customs")
		self.assertNotIn("link", icon)
		self.assertNotIn("sidebar", icon)
		self.assertEqual(home["type"], "Link")
		self.assertEqual(home["link_type"], "Workspace")
		self.assertEqual(home["link_to"], "Customs")
		self.assertEqual(sidebar["module"], "Customs")
		self.assertEqual(_grid_href(icon), "/desk/customs")

	def test_external_app_link_is_what_the_grid_used_to_open(self):
		stale = {
			"label": "Customs",
			"name": "Customs",
			"link_type": "External",
			"link": "/app/customs",
		}
		self.assertEqual(_grid_href(stale), "/app/customs")
		self.assertTrue(apply_desk_route(stale))
		self.assertEqual(stale["link_type"], DESK_ROUTE["link_type"])
		self.assertEqual(stale["link_to"], "Customs")
		self.assertIsNone(stale["link"])
		self.assertFalse(stale.get("sidebar"))
		self.assertEqual(_grid_href(stale), "/desk/customs")
		self.assertFalse(apply_desk_route(stale))

	def test_a_set_sidebar_would_skip_routing(self):
		icon = {
			"label": "Customs",
			"name": "Customs",
			"link_type": "Workspace Sidebar",
			"link_to": "Customs",
			"sidebar": "Customs",
		}
		self.assertIsNone(_grid_href(icon))
		self.assertTrue(apply_desk_route(icon))
		self.assertIsNone(icon["sidebar"])
		self.assertEqual(_grid_href(icon), "/desk/customs")

	def test_saved_layout_rewrites_a_nested_customs_tile_only(self):
		layout = [
			{"label": "Transport", "name": "Transport", "link_type": "Workspace Sidebar", "link_to": "Transport"},
			{
				"label": "Logistics",
				"icon_type": "Folder",
				"child_icons": [
					{"label": "Customs", "name": "Customs", "link_type": "External", "link": "/app/customs"},
					{"label": "Customs Notes", "name": "Customs Notes", "link": "/app/customs"},
				],
			},
		]
		self.assertTrue(walk_icons(layout))
		nested = layout[1]["child_icons"][0]
		self.assertEqual(nested["link_type"], "Workspace Sidebar")
		self.assertIsNone(nested["link"])
		self.assertEqual(layout[0]["link_to"], "Transport")
		self.assertEqual(layout[1]["child_icons"][1]["link"], "/app/customs")
		self.assertFalse(is_customs_tile(layout[1]["child_icons"][1]))
		self.assertFalse(walk_icons(layout))

	def test_document_fields_follow_the_same_route(self):
		class Icon:
			name = "Customs"
			label = "Customs"
			link_type = "External"
			link = "/app/customs"
			link_to = None
			sidebar = "Customs"

		icon = Icon()
		self.assertTrue(apply_desk_route_to_doc(icon))
		self.assertEqual(icon.link_type, "Workspace Sidebar")
		self.assertEqual(icon.link_to, "Customs")
		self.assertIsNone(icon.link)
		self.assertIsNone(icon.sidebar)
		self.assertFalse(apply_desk_route_to_doc(icon))

	def test_patch_is_registered_after_the_external_link_patches(self):
		lines = PATCHES_PATH.read_text().splitlines()
		external = lines.index("logistics.patches.v1_0_fix_customs_desktop_icon_route_and_cache")
		layouts = lines.index("logistics.patches.v1_0_fix_customs_in_saved_desktop_layouts")
		desk = lines.index("logistics.patches.v3_0_point_customs_desktop_icon_at_desk")
		self.assertLess(external, layouts)
		self.assertLess(layouts, desk)


if __name__ == "__main__":
	unittest.main()
