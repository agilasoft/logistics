# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
"""Force-sync Air Freight Control Tower page script from the app file.

Frappe can keep a stale ``tabPage.script`` after the on-disk page JS changes.
Reload the script from the module file and clear Page caches so desk clients
pick up Company / Branch / Cost Center / Profit Center / UNLOCO filters.
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

	with open(js_path, "r", encoding="utf-8") as fh:
		script = fh.read()

	if not frappe.db.exists("Page", PAGE_NAME):
		return

	frappe.db.set_value("Page", PAGE_NAME, "script", script, update_modified=True)
	frappe.db.commit()

	frappe.clear_cache(doctype="Page")
	try:
		frappe.cache().delete_keys("page_name_map")
	except Exception:
		pass
	try:
		frappe.cache().delete_value("page_name_map")
	except Exception:
		pass
