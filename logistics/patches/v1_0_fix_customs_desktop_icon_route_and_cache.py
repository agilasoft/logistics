# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt
"""Customs desktop tile: ensure External /app/customs link and clear stale boot cache.

Frappe caches per-user ``desktop_icons`` in Redis. After changing link_type/link, old
cache can omit ``link``, so ``get_route()`` skips the External branch and the tile
clicks with: "Icon is not correctly configured please check the workspace sidebar".
"""

import frappe


def execute():
	if not frappe.db.exists("Desktop Icon", "Customs"):
		return

	doc = frappe.get_doc("Desktop Icon", "Customs")
	doc.link_type = "External"
	doc.link = "/app/customs"
	doc.link_to = None
	doc.sidebar = None
	doc.save(ignore_permissions=True)

	# Same as Desktop Icon on_update for standard icons — flush cached desk payloads
	frappe.cache.delete_key("desktop_icons")
	frappe.cache.delete_key("bootinfo")
	frappe.clear_cache()
