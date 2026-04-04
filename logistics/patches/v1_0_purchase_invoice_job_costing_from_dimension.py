# Copyright (c) 2025, www.agilasoft.com and contributors
# License: MIT. See LICENSE

"""
Job Number (accounting dimension) on Purchase Invoice must come from the Accounting Dimension
definition (ERPNext adds it to Purchase Invoice via accounting_dimension_doctypes),
not from a logistics custom field.

This patch:
1. Removes duplicate Purchase Invoice custom fields named ``job_costing_number`` or
   ``job_number`` if they exist (so ERPNext can (re)create the dimension field cleanly).
2. Ensures the field is created by the Accounting Dimension by calling
   make_dimension_in_accounting_doctypes for the Job Number dimension.
"""

import frappe


def execute():
    for suffix in ("job_costing_number", "job_number"):
        custom_field_name = f"Purchase Invoice-{suffix}"
        if frappe.db.exists("Custom Field", custom_field_name):
            frappe.delete_doc(
                "Custom Field", custom_field_name, force=True, ignore_permissions=True
            )
    frappe.db.commit()

    # Ensure Job Number dimension adds the field to Purchase Invoice and other doctypes
    dim_name = None
    if frappe.db.exists("Accounting Dimension", "Job Number"):
        dim_name = "Job Number"
    elif frappe.db.exists("Accounting Dimension", "Job Costing Number"):
        dim_name = "Job Costing Number"

    if dim_name:
        from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
            make_dimension_in_accounting_doctypes,
        )

        doc = frappe.get_doc("Accounting Dimension", dim_name)
        make_dimension_in_accounting_doctypes(doc=doc)
        frappe.db.commit()

    return True
