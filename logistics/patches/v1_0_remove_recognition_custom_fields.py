# Copyright (c) 2025, www.agilasoft.com and contributors
# License: MIT. See LICENSE

"""
Migrate patch: Remove Revenue & Cost Recognition Custom Fields that are now in doctype JSON.

Recognition fields are now defined in the DocType JSON for:
- Air Shipment, Sea Shipment, Transport Job, Warehouse Job, Declaration, General Job
- Air Shipment Charges, Sea Shipment Charges, Warehouse Job Charges, Declaration Charges

This patch removes the legacy Custom Field records to avoid duplicates.
"""

import frappe


def execute():
    """Remove recognition Custom Fields that are now in doctype JSON."""
    job_doctypes = [
        "Air Shipment",
        "Sea Shipment",
        "Transport Job",
        "Warehouse Job",
        "Declaration",
        "General Job",
    ]
    job_fieldnames = [
        "recognition_section",
        "wip_recognition_enabled",
        "wip_recognition_date_basis",
        "accrual_recognition_enabled",
        "accrual_recognition_date_basis",
        "recognition_date",
        "column_break_recognition",
        "estimated_revenue",
        "wip_amount",
        "recognized_revenue",
        "wip_journal_entry",
        "wip_adjustment_journal_entry",
        "wip_closed",
        "column_break_accrual",
        "estimated_costs",
        "accrual_amount",
        "recognized_costs",
        "accrual_journal_entry",
        "accrual_adjustment_journal_entry",
        "accrual_closed",
    ]
    charges_doctypes = [
        "Air Shipment Charges",
        "Sea Shipment Charges",
        "Sea Freight Charges",
        "Warehouse Job Charges",
        "Declaration Charges",
    ]
    charges_fieldnames = ["estimated_revenue", "estimated_cost"]

    removed = 0
    for dt in job_doctypes:
        for fn in job_fieldnames:
            name = f"{dt}-{fn}"
            if frappe.db.exists("Custom Field", name):
                frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True)
                frappe.db.commit()
                removed += 1
                print(f"Removed Custom Field (now in doctype): {name}")

    for dt in charges_doctypes:
        for fn in charges_fieldnames:
            name = f"{dt}-{fn}"
            if frappe.db.exists("Custom Field", name):
                frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True)
                frappe.db.commit()
                removed += 1
                print(f"Removed Custom Field (now in doctype): {name}")

    if removed:
        print(f"Removed {removed} recognition Custom Field(s)")
    return True
