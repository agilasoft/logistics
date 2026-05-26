# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Add Exhibits desktop icon to saved Desktop Layout snapshots."""

from __future__ import annotations

import json

import frappe
from frappe.boot import get_bootinfo
from frappe.desk.doctype.desktop_icon.desktop_icon import get_desktop_icons


def _insert_index(layout: list) -> int:
	for i, icon in enumerate(layout):
		if isinstance(icon, dict) and icon.get("label") in (
			"Special Projects",
			"Exhibits",
			"Exhibits",
			"Show",
		):
			return i + 1
	return len(layout)


def execute():
	events_icon = None
	boot = get_bootinfo()
	for icon in get_desktop_icons(bootinfo=boot):
		if icon.get("label") == "Exhibits":
			events_icon = dict(icon)
			events_icon["child_icons"] = []
			break
	if not events_icon:
		return

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
		if "Exhibits" in labels:
			continue
		insert_at = _insert_index(layout)
		if insert_at > 0:
			prev = layout[insert_at - 1]
			events_icon["idx"] = (prev.get("idx") or insert_at) + 1
		layout.insert(insert_at, events_icon)
		doc = frappe.get_doc("Desktop Layout", row.name)
		doc.layout = json.dumps(layout)
		doc.save(ignore_permissions=True)
		updated += 1

	if updated:
		frappe.db.commit()
		frappe.cache.delete_key("desktop_icons")
		frappe.cache.delete_key("bootinfo")
