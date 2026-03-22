# Copyright (c) 2025, www.agilasoft.com and contributors
# License: MIT. See LICENSE

"""
Drop the deprecated 'function' column from tabUNLOCO.
UNLOCO now uses the Function Capabilities tab (has_seaport, has_road, etc.) instead.
"""

import frappe


def execute():
    if not frappe.db.table_exists("UNLOCO"):
        return
    if frappe.db.has_column("UNLOCO", "function"):
        frappe.db.sql("ALTER TABLE `tabUNLOCO` DROP COLUMN `function`")
        frappe.db.commit()
        print("Dropped column 'function' from tabUNLOCO")
