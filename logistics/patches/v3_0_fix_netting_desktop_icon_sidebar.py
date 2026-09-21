# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt
"""Netting desk tile: drop ``sidebar`` so the icon can resolve a route.

Frappe ``desktop.js`` skips ``get_route()`` when ``icon_data.sidebar`` is set.
The unhide patch copied ``sidebar: Netting`` into saved Desktop Layouts, so the
tile clicks with: "Icon is not correctly configured please check the workspace sidebar".
Working modules (Air Freight, Time Sensitive, …) keep ``sidebar`` empty.
"""

from __future__ import annotations

import json

import frappe


def execute():
	_clear_desktop_icon_sidebar()
	_fix_desktop_layouts()
	frappe.cache.delete_key("desktop_icons")
	frappe.cache.delete_key("bootinfo")
	frappe.clear_cache()


def _clear_desktop_icon_sidebar():
	if not frappe.db.exists("Desktop Icon", "Netting"):
		return
	doc = frappe.get_doc("Desktop Icon", "Netting")
	doc.sidebar = None
	doc.link_type = "Workspace Sidebar"
	doc.link_to = "Netting"
	doc.link = None
	doc.hidden = 0
	doc.flags.ignore_validate = True
	doc.save(ignore_permissions=True)


def _fix_icon_dict(icon: dict) -> bool:
	if icon.get("label") != "Netting" and icon.get("name") != "Netting":
		return False
	if icon.get("name") not in (None, "Netting"):
		return False
	changed = False
	wanted = {
		"link_type": "Workspace Sidebar",
		"link_to": "Netting",
		"sidebar": None,
		"hidden": 0,
	}
	for key, value in wanted.items():
		if icon.get(key) != value:
			icon[key] = value
			changed = True
	return changed


def _walk_icons(layout_list: list) -> bool:
	changed = False
	for icon in layout_list:
		if not isinstance(icon, dict):
			continue
		if _fix_icon_dict(icon):
			changed = True
		children = icon.get("child_icons") or []
		if children and isinstance(children, list) and _walk_icons(children):
			changed = True
	return changed


def _fix_desktop_layouts():
	for row in frappe.get_all("Desktop Layout", fields=["name", "layout"]):
		if not row.layout:
			continue
		try:
			layout = json.loads(row.layout)
		except Exception:
			continue
		if not isinstance(layout, list):
			continue
		if not _walk_icons(layout):
			continue
		doc = frappe.get_doc("Desktop Layout", row.name)
		doc.layout = json.dumps(layout)
		doc.save(ignore_permissions=True)
