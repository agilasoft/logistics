# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Add purchase_invoice_status and purchase_invoice to charge doctypes for PI request tagging."""

import frappe

CHARGE_DOCTYPES = [
    "Transport Job Charges",
    "Air Shipment Charges",
    "Sea Shipment Charges",
    "Warehouse Job Charges",
    "Declaration Charges",
]

INSERT_AFTER_FALLBACKS = ("quantity", "charge_item", "item_code", "rate", "buying_amount")


def _find_insert_after(meta, fallbacks):
    for name in fallbacks:
        if meta.get_field(name):
            return name
    return None


def execute():
    for dt in CHARGE_DOCTYPES:
        if not frappe.db.exists("DocType", dt):
            continue
        meta = frappe.get_meta(dt)
        insert_after = _find_insert_after(meta, INSERT_AFTER_FALLBACKS)
        if not insert_after:
            continue

        if not meta.get_field("purchase_invoice_status"):
            frappe.get_doc({
                "doctype": "Custom Field",
                "dt": dt,
                "fieldname": "purchase_invoice_status",
                "fieldtype": "Select",
                "label": "Cost Invoice Status",
                "options": "Not Requested\nRequested\nInvoiced",
                "default": "Not Requested",
                "insert_after": insert_after,
                "read_only": 1,
                "description": "Set to Requested when included in a Purchase Invoice request; row becomes read-only.",
            }).insert(ignore_permissions=True)

        meta = frappe.get_meta(dt)
        if not meta.get_field("purchase_invoice"):
            frappe.get_doc({
                "doctype": "Custom Field",
                "dt": dt,
                "fieldname": "purchase_invoice",
                "fieldtype": "Link",
                "label": "Purchase Invoice",
                "options": "Purchase Invoice",
                "insert_after": "purchase_invoice_status",
                "read_only": 1,
                "description": "Purchase Invoice this charge was requested in.",
            }).insert(ignore_permissions=True)

    frappe.db.commit()
