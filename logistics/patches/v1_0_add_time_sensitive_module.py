# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Register Time Sensitive module desk assets, roles, and default case types."""

from __future__ import annotations

import json
import os

import frappe
from frappe.boot import get_bootinfo
from frappe.desk.doctype.desktop_icon.desktop_icon import get_desktop_icons
from frappe.modules.import_file import import_file_by_path
from frappe.modules.utils import get_app_level_directory_path


ROLES = (
	"Time Sensitive Manager",
	"Time Sensitive Coordinator",
	"Time Sensitive Operator",
	"Time Sensitive Viewer",
)


def execute():
	_ensure_module_def()
	_ensure_roles()
	_import_desk_assets()
	_ensure_workspace()
	_seed_case_types()
	updated = _add_to_desktop_layouts()
	frappe.db.commit()
	frappe.cache.delete_key("desktop_icons")
	frappe.cache.delete_key("bootinfo")
	frappe.clear_cache()
	if updated:
		frappe.msgprint(f"Added Time Sensitive to {updated} Desktop Layout(s).")


def _ensure_module_def():
	if frappe.db.exists("Module Def", "Time Sensitive"):
		return
	doc = frappe.new_doc("Module Def")
	doc.app_name = "logistics"
	doc.module_name = "Time Sensitive"
	doc.insert(ignore_permissions=True)


def _ensure_roles():
	for role in ROLES:
		if frappe.db.exists("Role", role):
			continue
		doc = frappe.new_doc("Role")
		doc.role_name = role
		doc.desk_access = 1
		doc.insert(ignore_permissions=True)


def _import_desk_assets():
	app = "logistics"
	paths = [
		os.path.join(get_app_level_directory_path("workspace_sidebar", app), "time_sensitive.json"),
		os.path.join(get_app_level_directory_path("desktop_icon", app), "time_sensitive.json"),
	]
	for path in paths:
		if os.path.exists(path):
			import_file_by_path(path, force=True)

	if frappe.db.exists("Desktop Icon", "Time Sensitive"):
		doc = frappe.get_doc("Desktop Icon", "Time Sensitive")
		doc.label = "Time Sensitive"
		doc.link_to = "Time Sensitive"
		doc.link_type = "Workspace Sidebar"
		doc.hidden = 0
		doc.save(ignore_permissions=True)


def _ensure_workspace():
	if frappe.db.exists("Workspace", "Time Sensitive"):
		return
	app_path = frappe.get_app_path("logistics")
	workspace_path = os.path.join(
		app_path, "time_sensitive", "workspace", "time_sensitive", "time_sensitive.json"
	)
	if os.path.exists(workspace_path):
		import_file_by_path(workspace_path, force=True)


def _seed_case_types():
	try:
		from logistics.time_sensitive.doctype.time_sensitive_case_type.time_sensitive_case_type import (
			seed_default_case_types,
		)

		seed_default_case_types()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "seed_time_sensitive_case_types")


def _insert_index(layout: list) -> int:
	for i, icon in enumerate(layout):
		if isinstance(icon, dict) and icon.get("label") in (
			"High Value",
			"Exhibits",
			"Special Projects",
			"Time Sensitive",
		):
			return i + 1
	return len(layout)


def _add_to_desktop_layouts() -> int:
	ts_icon = None
	boot = get_bootinfo()
	for icon in get_desktop_icons(bootinfo=boot):
		if icon.get("label") == "Time Sensitive":
			ts_icon = dict(icon)
			ts_icon["child_icons"] = []
			break
	if not ts_icon:
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
		if "Time Sensitive" in labels:
			continue
		insert_at = _insert_index(layout)
		if insert_at > 0:
			prev = layout[insert_at - 1]
			ts_icon["idx"] = (prev.get("idx") or insert_at) + 1
		layout.insert(insert_at, ts_icon)
		doc = frappe.get_doc("Desktop Layout", row.name)
		doc.layout = json.dumps(layout)
		doc.save(ignore_permissions=True)
		updated += 1

	return updated
