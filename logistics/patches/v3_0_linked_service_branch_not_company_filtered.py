# Copyright (c) 2026, Agilasoft and contributors
"""Linked Service: Branch is not filtered by Company.

Only Cost Center is company-filtered. Drop the Branch.custom_company
link filter so the full form matches the Manage Linked Services dialog.
"""

import frappe


def execute():
	cleared = []
	for parent in ("Linked Service", "Linked Service Detail"):
		name = frappe.db.get_value(
			"DocField",
			{"parent": parent, "fieldname": "branch"},
			"name",
		)
		if not name:
			continue
		if not frappe.db.get_value("DocField", name, "link_filters"):
			continue
		frappe.db.set_value("DocField", name, "link_filters", None, update_modified=False)
		cleared.append(parent)

	if cleared:
		frappe.clear_cache(doctype="Linked Service")
		frappe.clear_cache(doctype="Linked Service Detail")
