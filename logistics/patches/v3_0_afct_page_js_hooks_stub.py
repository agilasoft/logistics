# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
"""Force Air Freight Control Tower to use hooks page_js asset.

Rewrites ``tabPage.script`` to the thin stub so stale inline page JS
(Organization / missing filters) cannot overwrite the asset-loaded UI.

Older Frappe versions stored page JS in ``tabPage.script``. Current Frappe
loads page assets from disk via ``Page.load_assets()``, so there is no
``script`` column — in that case only clear Page caches.
"""

from __future__ import unicode_literals

import os

import frappe


PAGE_NAME = "air-freight-control-tower"


def execute():
	js_path = frappe.get_app_path(
		"logistics",
		"air_freight",
		"page",
		"air_freight_control_tower",
		"air_freight_control_tower.js",
	)
	if not os.path.exists(js_path):
		return
	if not frappe.db.exists("Page", PAGE_NAME):
		return

	# Legacy installs only: refresh DB-stored script when the column exists.
	if frappe.db.has_column("Page", "script"):
		with open(js_path, "r", encoding="utf-8") as fh:
			script = fh.read()
		frappe.db.set_value("Page", PAGE_NAME, "script", script, update_modified=True)
		frappe.db.commit()

	frappe.clear_cache(doctype="Page")
	try:
		frappe.clear_cache()
	except Exception:
		pass
