# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Drop saved CargoNext dock arrangements so the shipped order is the rail.

An older arrangement still draws the line icons ahead of the module tiles.
The standard dock is the list again after this runs.
"""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.table_exists("tabDock"):
		return
	if not frappe.db.exists("Dock", {"app": "logistics", "standard": 1}):
		return

	names = frappe.get_all("Dock", filters={"app": "logistics", "standard": 0}, pluck="name")
	for name in names:
		frappe.delete_doc("Dock", name, force=True, ignore_permissions=True)
	if names:
		frappe.clear_cache()
