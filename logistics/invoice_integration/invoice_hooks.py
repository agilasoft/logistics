# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Doc event hooks for Sales Invoice and Purchase Invoice to update
linked logistics jobs/shipments (lifecycle and cancellation).
"""

import frappe
from .lifecycle import (
    update_job_on_sales_invoice_submit,
    update_job_on_sales_invoice_cancel,
    update_job_on_purchase_invoice_submit,
    update_job_on_purchase_invoice_cancel,
)


def on_sales_invoice_submit(doc, method=None):
    """Update linked jobs when SI is submitted."""
    if doc.docstatus != 1:
        return
    update_job_on_sales_invoice_submit(doc)


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
