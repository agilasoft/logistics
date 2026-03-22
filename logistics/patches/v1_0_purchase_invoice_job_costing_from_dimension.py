# Copyright (c) 2025, www.agilasoft.com and contributors
# License: MIT. See LICENSE

"""
Job Costing Number on Purchase Invoice must come from the Accounting Dimension
definition (ERPNext adds it to Purchase Invoice via accounting_dimension_doctypes),
not from a logistics custom field.

This patch:
1. Removes the logistics-origin Custom Field job_costing_number from Purchase Invoice
   if it exists.
2. Ensures the field is created by the Accounting Dimension by calling
   make_dimension_in_accounting_doctypes for the Job Costing Number dimension.
"""

import frappe


def execute():
    custom_field_name = "Purchase Invoice-job_costing_number"
    if frappe.db.exists("Custom Field", custom_field_name):
        frappe.delete_doc("Custom Field", custom_field_name, force=True, ignore_permissions=True)
        frappe.db.commit()

    # Ensure Job Costing Number dimension adds the field to Purchase Invoice and other doctypes
    if frappe.db.exists("Accounting Dimension", "Job Costing Number"):
        from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
            make_dimension_in_accounting_doctypes,
        )

        doc = frappe.get_doc("Accounting Dimension", "Job Costing Number")
        make_dimension_in_accounting_doctypes(doc=doc)
        frappe.db.commit()

    return True
