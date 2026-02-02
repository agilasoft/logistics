# Copyright (c) 2025, www.agilasoft.com and contributors
# License: MIT. See LICENSE

"""
Remove duplicate Custom Field that causes IntegrityError during sync_customizations.

Custom Field "Air Shipment-estimated_revenue" may already exist. When sync_customizations
runs it tries to INSERT from JSON and fails with Duplicate entry. Delete the existing
field so sync can insert it from the JSON.
"""

import frappe


def execute():
    custom_field_name = "Air Shipment-estimated_revenue"
    if frappe.db.exists("Custom Field", custom_field_name):
        frappe.delete_doc("Custom Field", custom_field_name, force=True, ignore_permissions=True)
        frappe.db.commit()
        print(f"Removed duplicate Custom Field: {custom_field_name}")
    return True
