# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt
"""Customs desktop tile: open the module sidebar, and clear the cached grid.

An External ``/app/customs`` link is copied into the tile href. ``/app`` is the
desk's old prefix, so the icon left the desk. Workspace Sidebar resolves
through the Customs sidebar, whose home is ``/desk/customs``.

Frappe caches per-user ``desktop_icons`` in Redis. A stale payload with no
route makes the tile report that it is not configured.
"""

import frappe

from logistics.customs.desktop_icon_route import apply_desk_route_to_doc


def execute():
	if not frappe.db.exists("Desktop Icon", "Customs"):
		return

	doc = frappe.get_doc("Desktop Icon", "Customs")
	if apply_desk_route_to_doc(doc):
		# link_to is a Dynamic Link aimed at the archived Workspace Sidebar doctype.
		doc.flags.ignore_validate = True
		doc.flags.ignore_links = True
		doc.save(ignore_permissions=True)

	# Same as Desktop Icon on_update for standard icons — flush cached desk payloads
	frappe.cache.delete_key("desktop_icons")
	frappe.cache.delete_key("bootinfo")
	frappe.clear_cache()
