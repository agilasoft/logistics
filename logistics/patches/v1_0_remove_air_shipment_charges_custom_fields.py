# Copyright (c) 2025, www.agilasoft.com and contributors
# License: MIT. See LICENSE

"""
Migrate patch: Remove Air Shipment Charges recognition Custom Fields that are now in the doctype.

estimated_revenue and estimated_cost are now defined in Air Shipment Charges doctype JSON
(air_shipment_charges.json). This patch removes the legacy Custom Field records so we do not
have duplicate definitions and sync_customizations no longer tries to insert them (which would
cause Duplicate entry 'Air Shipment Charges-estimated_revenue' for key 'PRIMARY').
"""

import frappe


def execute():
    """Remove Air Shipment Charges recognition Custom Fields if they exist."""
    for custom_field_name in (
        "Air Shipment Charges-estimated_revenue",
        "Air Shipment Charges-estimated_cost",
    ):
        if frappe.db.exists("Custom Field", custom_field_name):
            frappe.delete_doc("Custom Field", custom_field_name, force=True, ignore_permissions=True)
            frappe.db.commit()
            print(f"Removed Custom Field (now in doctype): {custom_field_name}")
    return True
