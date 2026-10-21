# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt
"""Open the Customs desktop tile on /desk/customs.

The tile was saved as an External link to ``/app/customs``. The desktop grid
uses an External ``link`` as the href, so the status bar and the click both
stay on ``/app``. Every other logistics tile is a Workspace Sidebar link, and
the Customs sidebar's home is the Customs workspace at ``/desk/customs``.

Sites that already ran the earlier External-link patches still have that
``/app/customs`` value on the Desktop Icon and in per-user Desktop Layout
snapshots. Those snapshots are what the desk draws when they are non-empty.
"""

from __future__ import annotations

import json

import frappe

from logistics.customs.desktop_icon_route import apply_desk_route_to_doc, walk_icons


def execute():
	_fix_desktop_icon()
	_fix_desktop_layouts()
	frappe.cache.delete_key("desktop_icons")
	frappe.cache.delete_key("bootinfo")
	frappe.clear_cache()


def _fix_desktop_icon():
	if not frappe.db.exists("Desktop Icon", "Customs"):
		return
	doc = frappe.get_doc("Desktop Icon", "Customs")
	if not apply_desk_route_to_doc(doc):
		return
	# link_to is a Dynamic Link aimed at the archived Workspace Sidebar doctype.
	doc.flags.ignore_validate = True
	doc.flags.ignore_links = True
	doc.save(ignore_permissions=True)


def _fix_desktop_layouts():
	if not frappe.db.table_exists("Desktop Layout"):
		return
	for row in frappe.get_all("Desktop Layout", fields=["name", "layout"]):
		if not row.layout:
			continue
		try:
			layout = json.loads(row.layout)
		except Exception:
			continue
		if not walk_icons(layout):
			continue
		doc = frappe.get_doc("Desktop Layout", row.name)
		doc.layout = json.dumps(layout)
		doc.save(ignore_permissions=True)
