# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt
"""Point Customs at the desk inside per-user Desktop Layout snapshots.

The desk page uses ``Desktop Layout`` JSON as ``frappe.desktop_icons`` when it
is non-empty. Those snapshots can still list Customs as an External
``/app/customs`` link, or as a Workspace Sidebar row with ``link`` empty and
``sidebar`` set. Either shape misses ``/desk/customs``.
"""

import json

import frappe

from logistics.customs.desktop_icon_route import walk_icons


def execute():
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

	frappe.cache.delete_key("desktop_icons")
	frappe.clear_cache()
