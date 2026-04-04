# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe


def execute():
    """Drop legacy route_sequence field from Sea Consolidation Routes."""
    if frappe.db.has_column("Sea Consolidation Routes", "route_sequence"):
        frappe.db.sql("ALTER TABLE `tabSea Consolidation Routes` DROP COLUMN `route_sequence`")
