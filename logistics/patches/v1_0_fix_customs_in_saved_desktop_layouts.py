# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt
"""Fix Customs tile in per-user Desktop Layout snapshots.

The desk page uses ``Desktop Layout`` JSON as ``frappe.desktop_icons`` when non-empty.
Those snapshots can still list Customs as ``Workspace Sidebar`` with ``link: null``, so
``get_route()`` returns nothing and the tile shows the workspace-sidebar error — even when
``tabDesktop Icon`` was already fixed to External ``/app/customs``.
"""

import json

import frappe


def _fix_customs_icon_dict(icon: dict) -> bool:
	if icon.get("label") != "Customs":
		return False
	if icon.get("name") not in (None, "Customs"):
		return False
	if (
		icon.get("link_type") == "External"
		and icon.get("link") == "/app/customs"
		and icon.get("link_to") in (None, "")
	):
		return False
	icon["link_type"] = "External"
	icon["link"] = "/app/customs"
	icon["link_to"] = None
	return True


def _walk_icons(layout_list: list) -> bool:
	changed = False
	for icon in layout_list:
		if not isinstance(icon, dict):
			continue
		if _fix_customs_icon_dict(icon):
			changed = True
		children = icon.get("child_icons") or []
		if children and isinstance(children, list) and _walk_icons(children):
			changed = True
	return changed


def execute():
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

	frappe.cache.delete_key("desktop_icons")
	frappe.clear_cache()
