# Copyright (c) 2026, Agilasoft and contributors
"""Use the logistics blue Netting desk tile (SVG + bg_color) on saved layouts."""

from __future__ import annotations

import json
import os

import frappe
from frappe.modules.import_file import import_file_by_path
from frappe.modules.utils import get_app_level_directory_path


def execute():
	_import_desktop_icon()
	_normalize_desktop_icon()
	_update_desktop_layouts()
	frappe.cache.delete_key("desktop_icons")
	frappe.cache.delete_key("bootinfo")
	frappe.clear_cache()


def _import_desktop_icon():
	path = os.path.join(get_app_level_directory_path("desktop_icon", "logistics"), "netting.json")
	if os.path.isfile(path):
		import_file_by_path(path, force=True)


def _normalize_desktop_icon():
	if not frappe.db.exists("Desktop Icon", "Netting"):
		return
	doc = frappe.get_doc("Desktop Icon", "Netting")
	doc.app = "logistics"
	doc.bg_color = "blue"
	doc.label = "Netting"
	doc.link_to = "Netting"
	doc.link_type = "Workspace Sidebar"
	doc.sidebar = None
	doc.hidden = 0
	doc.standard = 1
	doc.icon = None
	doc.flags.ignore_validate = True
	doc.save(ignore_permissions=True)


def _fix_icon_dict(icon: dict) -> bool:
	if icon.get("label") != "Netting" and icon.get("name") != "Netting":
		return False
	changed = False
	wanted = {
		"app": "logistics",
		"bg_color": "blue",
		"link_type": "Workspace Sidebar",
		"link_to": "Netting",
		"sidebar": None,
		"standard": 1,
		"icon": None,
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


def _update_desktop_layouts():
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
