# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors

"""Add default_cost_supplier to Logistics Settings for Purchase Invoice creation."""

import frappe


def execute():
    if not frappe.db.exists("DocType", "Logistics Settings"):
        return
    
    meta = frappe.get_meta("Logistics Settings")
    if meta.get_field("default_cost_supplier"):
        return
    
    doc = frappe.get_doc({
        "doctype": "Custom Field",
        "dt": "Logistics Settings",
        "fieldname": "default_cost_supplier",
        "fieldtype": "Link",
        "label": "Default Cost Supplier",
        "options": "Supplier",
        "insert_after": "default_chargeable_weight_uom",
        "description": "Default supplier when creating Purchase Invoice from job costs and charge has no pay_to",
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
