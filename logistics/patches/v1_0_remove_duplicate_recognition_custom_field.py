# Copyright (c) 2025, www.agilasoft.com and contributors
# License: MIT. See LICENSE

"""
Migrate patch: Remove duplicate Custom Field that causes IntegrityError during sync_customizations.

The recognition custom field "Air Shipment Charges-estimated_revenue" can already exist in the
database (e.g. from install_recognition_fields or a previous sync). When sync_customizations runs
it may try to INSERT the same field from job_management/custom/recognition_fields.json and fail with:
  Duplicate entry 'Air Shipment Charges-estimated_revenue' for key 'PRIMARY'

This patch deletes the existing Custom Field so that sync_customizations can insert it from the
JSON, ensuring a single source of truth.
"""

import frappe


def execute():
    """Remove duplicate recognition Custom Field if it exists."""
    custom_field_name = "Air Shipment Charges-estimated_revenue"
    if frappe.db.exists("Custom Field", custom_field_name):
        frappe.delete_doc("Custom Field", custom_field_name, force=True, ignore_permissions=True)
        frappe.db.commit()
        print(f"Removed duplicate Custom Field: {custom_field_name}")
    return True
