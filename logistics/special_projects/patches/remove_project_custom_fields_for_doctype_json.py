# Copyright (c) 2026, www.agilasoft.com and contributors
# One-time: remove project Custom Field so only the doctype JSON field remains.

import frappe

DOCTYPES = [
    "Transport Order", "Air Booking", "Sea Booking", "Inbound Order",
    "Release Order", "Transfer Order", "VAS Order", "Transport Job",
    "Warehouse Job", "Air Shipment", "Sea Shipment", "Declaration",
]


def execute():
    for dt in DOCTYPES:
        try:
            name = frappe.db.get_value("Custom Field", {"dt": dt, "fieldname": "project"}, "name")
            if name:
                frappe.delete_doc("Custom Field", name, force=True)
        except Exception as e:
            frappe.log_error(
                title=f"Special Projects: Remove project custom field from {dt}",
                message=str(e),
            )
    frappe.db.commit()
