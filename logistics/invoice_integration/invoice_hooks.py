# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Doc event hooks for Sales Invoice and Purchase Invoice to update
linked logistics jobs/shipments (lifecycle and cancellation).
"""

import frappe
from frappe import _
from .lifecycle import (
    update_job_on_sales_invoice_submit,
    update_job_on_sales_invoice_cancel,
    update_job_on_purchase_invoice_submit,
    update_job_on_purchase_invoice_cancel,
)


def on_sales_invoice_submit(doc, method=None):
    """Update linked jobs when SI is submitted; create intercompany invoices if from Sales Quote."""
    if doc.docstatus != 1:
        return
    update_job_on_sales_invoice_submit(doc)
    # Intercompany: when customer SI is from a Sales Quote, create intercompany SI/PI for legs where job company != quote company
    try:
        from logistics.intercompany.intercompany_invoice import (
            is_intercompany_enabled,
            create_intercompany_invoices_for_quote,
        )
        if is_intercompany_enabled() and getattr(doc, "quotation_no", None):
            if frappe.db.exists("Sales Quote", doc.quotation_no):
                create_intercompany_invoices_for_quote(
                    sales_quote_name=doc.quotation_no,
                    billing_company=doc.company,
                    trigger_si=doc.name,
                    posting_date=doc.posting_date,
                )
    except Exception as e:
        frappe.log_error(
            title="Intercompany Invoices on SI Submit",
            message=frappe.get_traceback(),
        )
        frappe.msgprint(
            _("Intercompany invoices could not be created: {0}").format(str(e)),
            indicator="orange",
        )

    # Internal billing: when customer SI is from a Sales Quote, create Journal Entry for same-company Internal Jobs (no Sales Invoice)
    try:
        from logistics.billing.internal_billing import create_internal_billing_journal_entries_for_quote
        if getattr(doc, "quotation_no", None) and frappe.db.exists("Sales Quote", doc.quotation_no):
            result = create_internal_billing_journal_entries_for_quote(
                sales_quote_name=doc.quotation_no,
                billing_company=doc.company,
                trigger_si=doc.name,
                posting_date=doc.posting_date,
            )
            if result.get("created") and result.get("journal_entry"):
                frappe.msgprint(
                    _("Internal billing: {0}").format(result.get("message", "")),
                    indicator="blue",
                )
    except Exception as e:
        frappe.log_error(
            title="Internal Billing JV on SI Submit",
            message=frappe.get_traceback(),
        )
        frappe.msgprint(
            _("Internal billing Journal Entry could not be created: {0}").format(str(e)),
            indicator="orange",
        )


def on_sales_invoice_cancel(doc, method=None):
    """Clear links and reset statuses when SI is cancelled."""
    if doc.docstatus != 2:
        return
    update_job_on_sales_invoice_cancel(doc)


def on_purchase_invoice_submit(doc, method=None):
    """Update linked jobs when PI is submitted."""
    if doc.docstatus != 1:
        return
    update_job_on_purchase_invoice_submit(doc)


def on_purchase_invoice_cancel(doc, method=None):
    """Clear links and reset statuses when PI is cancelled."""
    if doc.docstatus != 2:
        return
    update_job_on_purchase_invoice_cancel(doc)
