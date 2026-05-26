# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Register High Value module desk assets and add tile to saved Desktop Layouts."""

from __future__ import annotations

import json
import os

import frappe
from frappe.boot import get_bootinfo
from frappe.desk.doctype.desktop_icon.desktop_icon import get_desktop_icons
from frappe.modules.import_file import import_file_by_path
from frappe.modules.utils import get_app_level_directory_path


def execute():
	_ensure_module_def()
	_import_high_value_desk_assets()
	_ensure_high_value_workspace()
	updated = _add_high_value_to_desktop_layouts()
	frappe.db.commit()
	frappe.cache.delete_key("desktop_icons")
	frappe.cache.delete_key("bootinfo")
	frappe.clear_cache()
	if updated:
		frappe.msgprint(f"Added High Value to {updated} Desktop Layout(s).")


def _ensure_module_def():
	if frappe.db.exists("Module Def", "High Value"):
		return
	doc = frappe.new_doc("Module Def")
	doc.app_name = "logistics"
	doc.module_name = "High Value"
	doc.insert(ignore_permissions=True)


def _import_high_value_desk_assets():
	app = "logistics"
	paths = [
		os.path.join(get_app_level_directory_path("workspace_sidebar", app), "high_value.json"),
		os.path.join(get_app_level_directory_path("desktop_icon", app), "high_value.json"),
	]
	for path in paths:
		if os.path.exists(path):
			import_file_by_path(path, force=True)

	if frappe.db.exists("Desktop Icon", "High Value"):
		doc = frappe.get_doc("Desktop Icon", "High Value")
		doc.label = "High Value"
		doc.link_to = "High Value"
		doc.link_type = "Workspace Sidebar"
		doc.hidden = 0
		doc.save(ignore_permissions=True)


def _ensure_high_value_workspace():
	if frappe.db.exists("Workspace", "High Value"):
		return
	app_path = frappe.get_app_path("logistics")
	workspace_path = os.path.join(
		app_path, "high_value", "workspace", "high_value", "high_value.json"
	)
	if os.path.exists(workspace_path):
		import_file_by_path(workspace_path, force=True)


def _insert_index(layout: list) -> int:
	for i, icon in enumerate(layout):
		if isinstance(icon, dict) and icon.get("label") in (
			"Exhibits",
			"Special Projects",
			"High Value",
		):
			return i + 1
	return len(layout)


def _add_high_value_to_desktop_layouts() -> int:
	high_value_icon = None
	boot = get_bootinfo()
	for icon in get_desktop_icons(bootinfo=boot):
		if icon.get("label") == "High Value":
			high_value_icon = dict(icon)
			high_value_icon["child_icons"] = []
			break
	if not high_value_icon:
		return 0

	updated = 0
	for row in frappe.get_all("Desktop Layout", fields=["name", "layout"]):
		if not row.layout:
			continue
		try:
			layout = json.loads(row.layout)
		except Exception:
			continue
		if not isinstance(layout, list):
			continue
		labels = {x.get("label") for x in layout if isinstance(x, dict)}
		if "High Value" in labels:
			continue
		insert_at = _insert_index(layout)
		if insert_at > 0:
			prev = layout[insert_at - 1]
			high_value_icon["idx"] = (prev.get("idx") or insert_at) + 1
		layout.insert(insert_at, high_value_icon)
		doc = frappe.get_doc("Desktop Layout", row.name)
		doc.layout = json.dumps(layout)
		doc.save(ignore_permissions=True)
		updated += 1

	return updated
