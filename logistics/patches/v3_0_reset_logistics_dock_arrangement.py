# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Drop saved CargoNext dock arrangements so the shipped module rail is what opens.

Frappe treats a saved site or user dock as the whole rail. Modules the layer
does not name stay off it. Arrangements saved while this dock was incomplete
hid the modules. The app dock is the list again after this runs; a later
arrangement still wins for the rows it names.
"""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.table_exists("tabDock"):
		return

	# Leave a site arrangement in place when the app dock itself did not import.
	# Deleting it then would remove the only rail the desk has.
	standard = frappe.db.get_value("Dock", {"app": "logistics", "standard": 1}, "name")
	if not standard or frappe.db.count("Dock Item", {"parent": standard}) < 19:
		return

	names = frappe.get_all("Dock", filters={"app": "logistics", "standard": 0}, pluck="name")
	for name in names:
		frappe.delete_doc("Dock", name, force=True, ignore_permissions=True)
	if names:
		frappe.clear_cache()
