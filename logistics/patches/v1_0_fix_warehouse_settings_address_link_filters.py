# Copyright (c) 2026, www.agilasoft.com and contributors
"""Remove invalid Address.link_doctype link_filters on Warehouse Settings.

link_doctype/link_name live on Dynamic Link child rows, not Address. JSON
link_filters made Frappe search_link filter Address.link_doctype and raised
PermissionError for roles without read on that non-existent field.
"""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Warehouse Settings"):
		return

	frappe.db.set_value(
		"DocField",
		{"parent": "Warehouse Settings", "fieldname": "warehouse_contract_address"},
		"link_filters",
		None,
	)
	frappe.clear_cache(doctype="Warehouse Settings")
