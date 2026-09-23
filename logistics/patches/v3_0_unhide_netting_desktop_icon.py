# Copyright (c) 2026, Agilasoft and contributors
"""Show the Netting desk tile: unhide it and add it to layouts that omit it."""

from __future__ import annotations

import json
import os

import frappe
from frappe.boot import get_bootinfo
from frappe.desk.doctype.desktop_icon.desktop_icon import get_desktop_icons
from frappe.modules.import_file import import_file_by_path
from frappe.modules.utils import get_app_level_directory_path


INSERT_AFTER = (
	"Intercompany",
	"Invoicing",
	"Cash Advance",
	"Job Management",
	"MICE",
)


def execute():
	_import_desktop_icon()
	_normalize_desktop_icon()
	icon = _netting_icon_payload()
	_update_desktop_layouts(icon)
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


def _netting_icon_payload():
	boot = get_bootinfo()
	for icon in get_desktop_icons(bootinfo=boot):
		if icon.get("label") == "Netting":
			payload = dict(icon)
			payload["hidden"] = 0
			payload["app"] = "logistics"
			payload["bg_color"] = "blue"
			payload["link_type"] = "Workspace Sidebar"
			payload["link_to"] = "Netting"
			payload["sidebar"] = None
			payload["standard"] = 1
			payload["child_icons"] = []
			return payload
	return {
		"label": "Netting",
		"name": "Netting",
		"app": "logistics",
		"bg_color": "blue",
		"link_type": "Workspace Sidebar",
		"link_to": "Netting",
		"icon_type": "Link",
		"standard": 1,
		"hidden": 0,
		"child_icons": [],
	}


def _insert_index(layout: list) -> int:
	labels = {icon.get("label"): i for i, icon in enumerate(layout) if isinstance(icon, dict)}
	for label in INSERT_AFTER:
		if label in labels:
			return labels[label] + 1
	return len(layout)


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
		"hidden": 0,
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


def _update_desktop_layouts(icon_payload):
	for row in frappe.get_all("Desktop Layout", fields=["name", "layout"]):
		if not row.layout:
			continue
		try:
			layout = json.loads(row.layout)
		except Exception:
			continue
		if not isinstance(layout, list):
			continue
		changed = _walk_icons(layout)
		labels = {x.get("label") for x in layout if isinstance(x, dict)}
		if "Netting" not in labels:
			insert_at = _insert_index(layout)
			payload = dict(icon_payload)
			if insert_at > 0:
				prev = layout[insert_at - 1]
				payload["idx"] = (prev.get("idx") or insert_at) + 1
			else:
				payload["idx"] = 1
			layout.insert(insert_at, payload)
			changed = True
		if not changed:
			continue
		doc = frappe.get_doc("Desktop Layout", row.name)
		doc.layout = json.dumps(layout)
		doc.save(ignore_permissions=True)
