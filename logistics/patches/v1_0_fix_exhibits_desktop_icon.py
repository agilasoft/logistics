# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Remove stale Events desk tile; show Exhibits icon and fix saved Desktop Layouts."""

from __future__ import annotations

import json
import os
import shutil

import frappe
from frappe.modules.import_file import import_file_by_path
from frappe.modules.utils import get_app_level_directory_path


def execute():
	_ensure_exhibits_svg_assets()
	_import_exhibits_desk_assets()
	_remove_stale_events_desktop_icon()
	updated = _fix_desktop_layouts()
	frappe.db.commit()
	frappe.cache.delete_key("desktop_icons")
	frappe.cache.delete_key("bootinfo")
	frappe.clear_cache()
	if updated:
		frappe.msgprint(f"Updated {updated} Desktop Layout(s): Events tile removed, Exhibits shown.")


def _ensure_exhibits_svg_assets():
	app_path = frappe.get_app_path("logistics")
	for variant in ("solid", "subtle"):
		src = os.path.join(app_path, "public", "icons", "desktop_icons", variant, "events.svg")
		dst = os.path.join(app_path, "public", "icons", "desktop_icons", variant, "exhibits.svg")
		if os.path.isfile(src) and not os.path.isfile(dst):
			try:
				shutil.copyfile(src, dst)
			except OSError:
				pass


def _import_exhibits_desk_assets():
	app = "logistics"
	paths = [
		os.path.join(get_app_level_directory_path("workspace_sidebar", app), "exhibits.json"),
		os.path.join(get_app_level_directory_path("desktop_icon", app), "exhibits.json"),
	]
	for path in paths:
		if os.path.exists(path):
			import_file_by_path(path, force=True)

	if frappe.db.exists("Desktop Icon", "Exhibits"):
		doc = frappe.get_doc("Desktop Icon", "Exhibits")
		doc.label = "Exhibits"
		doc.link_to = "Exhibits"
		doc.link_type = "Workspace Sidebar"
		doc.hidden = 0
		doc.save(ignore_permissions=True)


def _remove_stale_events_desktop_icon():
	if frappe.db.exists("Desktop Icon", "Events"):
		frappe.delete_doc("Desktop Icon", "Events", force=True, ignore_missing=True)


def _fix_desktop_layouts() -> int:
	from frappe.boot import get_bootinfo
	from frappe.desk.doctype.desktop_icon.desktop_icon import get_desktop_icons

	exhibits_boot = None
	for icon in get_desktop_icons(bootinfo=get_bootinfo()):
		if icon.get("label") == "Exhibits":
			exhibits_boot = dict(icon)
			exhibits_boot["child_icons"] = []
			break

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

		new_layout = []
		changed = False
		for icon in layout:
			if not isinstance(icon, dict):
				new_layout.append(icon)
				continue
			if icon.get("label") == "Events":
				changed = True
				continue
			if icon.get("label") == "Exhibits":
				if exhibits_boot:
					merged = dict(exhibits_boot)
					merged["idx"] = icon.get("idx", merged.get("idx"))
					merged["hidden"] = 0
					new_layout.append(merged)
				else:
					icon = dict(icon)
					icon["hidden"] = 0
					icon["label"] = "Exhibits"
					icon["link_to"] = "Exhibits"
					icon["name"] = "Exhibits"
					new_layout.append(icon)
				changed = True
				continue
			new_layout.append(icon)

		if not changed:
			continue

		doc = frappe.get_doc("Desktop Layout", row.name)
		doc.layout = json.dumps(new_layout)
		doc.save(ignore_permissions=True)
		updated += 1

	return updated
