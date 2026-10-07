# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Keep submitted logistics jobs when a Sales or Purchase Invoice is cancelled.

Desk Cancel loads every submitted document that references the invoice and
cancels those documents first. A submitted job is in that set because its
charge row links to the invoice, and cancelling the job is then blocked by
the invoice line that still points back at the job. The job stays submitted;
invoice cancel clears the charge link afterwards.
"""

from logistics.invoice_integration.lifecycle import merge_invoice_cancel_ignore_doctypes


def get_submitted_linked_docs(doctype, name, ignore_doctypes_on_cancel_all=None):
    from frappe.desk.form.linked_with import get_submitted_linked_docs as original

    ignore = merge_invoice_cancel_ignore_doctypes(doctype, ignore_doctypes_on_cancel_all)
    return original(doctype, name, ignore)


def cancel_all_linked_docs(
    docs=None,
    ignore_doctypes_on_cancel_all=None,
    root_doctype=None,
    root_name=None,
):
    from frappe.desk.form.linked_with import cancel_all_linked_docs as original

    ignore = merge_invoice_cancel_ignore_doctypes(root_doctype, ignore_doctypes_on_cancel_all)
    return original(
        docs=docs,
        ignore_doctypes_on_cancel_all=ignore,
        root_doctype=root_doctype,
        root_name=root_name,
    )
