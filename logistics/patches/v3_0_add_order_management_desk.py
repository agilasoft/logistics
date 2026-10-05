# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt
"""Give Order Management its own desk tile and sidebar.

A public workspace alone is nested under CargoNext. The tile stays top-level:
``sidebar`` and ``parent_icon`` stay empty so the desk can open the sidebar.
"""

from __future__ import annotations

import json
import os

import frappe
from frappe.boot import get_bootinfo
from frappe.desk.doctype.desktop_icon.desktop_icon import get_desktop_icons
from frappe.modules.import_file import import_file_by_path
from frappe.modules.utils import get_app_level_directory_path


LABEL = "Order Management"
INSERT_AFTER = ("Warehousing", "Time Sensitive", "Cash Advance", "Job Management")


def execute():
	_import_desk_assets()
	_normalize_desktop_icon()
	icon = _icon_payload()
	_update_desktop_layouts(icon)
	frappe.cache.delete_key("desktop_icons")
	frappe.cache.delete_key("bootinfo")
	frappe.clear_cache()


def _import_desk_assets():
	app = "logistics"
	paths = [
		os.path.join(
			frappe.get_app_path(app),
			"order_management",
			"workspace",
			"order_management",
			"order_management.json",
		),
		os.path.join(get_app_level_directory_path("workspace_sidebar", app), "order_management.json"),
		os.path.join(get_app_level_directory_path("desktop_icon", app), "order_management.json"),
	]
	for path in paths:
		if os.path.isfile(path):
			import_file_by_path(path, force=True)


def _normalize_desktop_icon():
	if not frappe.db.exists("Desktop Icon", LABEL):
		return
	doc = frappe.get_doc("Desktop Icon", LABEL)
	doc.app = "logistics"
	doc.bg_color = "blue"
	doc.label = LABEL
	doc.link_to = LABEL
	doc.link_type = "Workspace Sidebar"
	doc.sidebar = None
	doc.parent_icon = None
	doc.hidden = 0
	doc.standard = 1
	doc.icon = None
	doc.flags.ignore_validate = True
	doc.save(ignore_permissions=True)


def _icon_payload():
	boot = get_bootinfo()
	for icon in get_desktop_icons(bootinfo=boot):
		if icon.get("label") == LABEL:
			payload = dict(icon)
			payload["hidden"] = 0
			payload["app"] = "logistics"
			payload["bg_color"] = "blue"
			payload["link_type"] = "Workspace Sidebar"
			payload["link_to"] = LABEL
			payload["sidebar"] = None
			payload["parent_icon"] = None
			payload["standard"] = 1
			payload["icon"] = None
			payload["child_icons"] = []
			return payload
	return {
		"label": LABEL,
		"name": LABEL,
		"app": "logistics",
		"bg_color": "blue",
		"link_type": "Workspace Sidebar",
		"link_to": LABEL,
		"icon_type": "Link",
		"standard": 1,
		"hidden": 0,
		"parent_icon": None,
		"sidebar": None,
		"child_icons": [],
	}


def _insert_index(layout: list) -> int:
	labels = {icon.get("label"): i for i, icon in enumerate(layout) if isinstance(icon, dict)}
	for label in INSERT_AFTER:
		if label in labels:
			return labels[label] + 1
	return len(layout)


def _is_order_management(icon: dict) -> bool:
	return icon.get("label") == LABEL or icon.get("name") == LABEL


def _wanted(icon: dict) -> dict:
	icon = dict(icon)
	icon.update(
		{
			"label": LABEL,
			"name": icon.get("name") or LABEL,
			"app": "logistics",
			"bg_color": "blue",
			"link_type": "Workspace Sidebar",
			"link_to": LABEL,
			"sidebar": None,
			"parent_icon": None,
			"standard": 1,
			"hidden": 0,
			"icon": None,
			"child_icons": [],
		}
	)
	return icon


def _extract(layout_list: list):
	"""Drop every Order Management tile, including ones nested under CargoNext."""
	found = None

	def walk(items):
		nonlocal found
		kept = []
		for icon in items:
			if not isinstance(icon, dict):
				kept.append(icon)
				continue
			children = icon.get("child_icons") or []
			if isinstance(children, list) and children:
				icon["child_icons"] = walk(children)
			if _is_order_management(icon):
				found = icon
				continue
			kept.append(icon)
		return kept

	return walk(layout_list), found


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
		layout, existing = _extract(layout)
		payload = _wanted(existing or icon_payload)
		insert_at = _insert_index(layout)
		if insert_at > 0:
			prev = layout[insert_at - 1]
			payload["idx"] = (prev.get("idx") or insert_at) + 1
		else:
			payload["idx"] = 1
		layout.insert(insert_at, payload)
		doc = frappe.get_doc("Desktop Layout", row.name)
		doc.layout = json.dumps(layout)
		doc.save(ignore_permissions=True)
