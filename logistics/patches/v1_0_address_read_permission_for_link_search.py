# Copyright (c) 2025 Agilasoft. All rights reserved.
"""Align Address DocPerm with Frappe link-search behaviour.

List queries that filter Address via Dynamic Link (e.g. link_doctype for party-specific
address search) require Read on Address. Roles with only Select hit PermissionError on
link_doctype when picking or adding a primary address.
"""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Address"):
		return

	dt = frappe.get_doc("DocType", "Address")
	changed = False
	for row in dt.permissions:
		if row.select and not row.read:
			row.read = 1
			changed = True

	if changed:
		dt.save(ignore_permissions=True)
		frappe.clear_cache(doctype="Address")
