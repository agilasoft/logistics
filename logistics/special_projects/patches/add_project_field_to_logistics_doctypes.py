# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Project (Link to Project) is now in each doctype JSON. This patch removes any
existing Custom Field 'project' for these doctypes to avoid duplicates.
"""

import frappe


def execute():
    """Remove project custom field if exists; field is now in doctype JSON."""
    doctypes = [
        "Transport Order",
        "Air Booking",
        "Sea Booking",
        "Inbound Order",
        "Release Order",
        "Transfer Order",
        "VAS Order",
        "Transport Job",
        "Warehouse Job",
        "Air Shipment",
        "Sea Shipment",
        "Declaration",
    ]

    for dt in doctypes:
        try:
            _remove_project_custom_field_if_exists(dt)
        except Exception as e:
            frappe.log_error(
                title=f"Special Projects: Failed to add project field to {dt}",
                message=str(e),
            )
            print(f"Skipped {dt}: {e}")
    frappe.db.commit()


def _remove_project_custom_field_if_exists(dt):
    """Remove project custom field; field is now in doctype JSON."""
    name = frappe.db.get_value("Custom Field", {"dt": dt, "fieldname": "project"}, "name")
    if name:
        frappe.delete_doc("Custom Field", name, force=True)
