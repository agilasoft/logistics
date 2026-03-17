# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Extend Cost Invoice Status to Requested/Posted/Paid and add Revenue Invoice Status (Sales) on charges."""

import frappe

CHARGE_DOCTYPES = [
    "Transport Job Charges",
    "Air Shipment Charges",
    "Sea Shipment Charges",
    "Warehouse Job Charges",
    "Declaration Charges",
]

# Status options for monitoring: avoid duplicate posting
COST_STATUS_OPTIONS = "Not Requested\nRequested\nPosted\nPaid"
REVENUE_STATUS_OPTIONS = "Not Requested\nRequested\nPosted\nPaid"

INSERT_AFTER_FALLBACKS = ("quantity", "charge_item", "item_code", "rate", "buying_amount", "purchase_invoice")


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

        # 1. Extend purchase_invoice_status options to Requested, Posted, Paid
        if meta.get_field("purchase_invoice_status"):
            cf = frappe.db.get_value(
                "Custom Field",
                {"dt": dt, "fieldname": "purchase_invoice_status"},
                "name",
            )
            if cf:
                doc = frappe.get_doc("Custom Field", cf)
                doc.options = COST_STATUS_OPTIONS
                doc.save(ignore_permissions=True)
            # Migrate existing "Invoiced" to "Posted"
            if frappe.db.has_column(dt, "purchase_invoice_status"):
                frappe.db.sql(
                    "UPDATE `tab{0}` SET purchase_invoice_status = 'Posted' WHERE purchase_invoice_status = 'Invoiced'".format(dt)
                )

        # 2. Add sales_invoice_status and sales_invoice for revenue monitoring
        meta = frappe.get_meta(dt)
        insert_after = _find_insert_after(meta, ("purchase_invoice", "purchase_invoice_status") + INSERT_AFTER_FALLBACKS)
        if not insert_after:
            continue

        if not meta.get_field("sales_invoice_status"):
            frappe.get_doc({
                "doctype": "Custom Field",
                "dt": dt,
                "fieldname": "sales_invoice_status",
                "fieldtype": "Select",
                "label": "Revenue Invoice Status",
                "options": REVENUE_STATUS_OPTIONS,
                "default": "Not Requested",
                "insert_after": insert_after,
                "read_only": 1,
                "description": "Requested when included in Sales Invoice; Posted when SI submitted; Paid when SI paid.",
            }).insert(ignore_permissions=True)

        meta = frappe.get_meta(dt)
        if not meta.get_field("sales_invoice"):
            frappe.get_doc({
                "doctype": "Custom Field",
                "dt": dt,
                "fieldname": "sales_invoice",
                "fieldtype": "Link",
                "label": "Sales Invoice",
                "options": "Sales Invoice",
                "insert_after": "sales_invoice_status",
                "read_only": 1,
                "description": "Sales Invoice this charge was requested in.",
            }).insert(ignore_permissions=True)

    frappe.db.commit()
