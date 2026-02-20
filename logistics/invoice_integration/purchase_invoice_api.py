# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Create Purchase Invoice from logistics job/shipment costs.
"""

import frappe
from frappe import _
from frappe.utils import flt, today
from typing import Dict, Any, Optional, List, Tuple

JOB_DOCTYPES = ("Transport Job", "Air Shipment", "Sea Shipment", "Warehouse Job", "Declaration")

# Charge table and cost field mapping: (charges_field, cost_field, rate_field, qty_field, item_field, supplier_field)
CHARGE_CONFIG = {
    "Transport Job": ("charges", "estimated_cost", "unit_cost", "quantity", "item_code", "pay_to"),
    "Air Shipment": ("charges", "estimated_cost", "estimated_cost", "quantity", "item_code", None),
    "Sea Shipment": ("charges", "buying_amount", "buying_amount", None, "charge_item", "pay_to"),
    "Warehouse Job": ("charges", "total", "rate", "quantity", "item_code", None),
    "Declaration": ("charges", "estimated_cost", "unit_cost", "quantity", "item_code", None),
}


@frappe.whitelist()
def create_purchase_invoice(
    job_type: str,
    job_name: str,
    supplier: Optional[str] = None,
    posting_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create Purchase Invoice from job/shipment costs.
    
    Args:
        job_type: Transport Job, Air Shipment, Sea Shipment, Warehouse Job, or Declaration
        job_name: Name of the job document
        supplier: Optional default supplier (used when charges have no pay_to)
        posting_date: Optional posting date (default: today)
    
    Returns:
        dict with ok, message, purchase_invoice
    """
    if job_type not in JOB_DOCTYPES:
        frappe.throw(_("Invalid job type: {0}").format(job_type))
    
    if not frappe.db.exists(job_type, job_name):
        frappe.throw(_("{0} {1} does not exist.").format(job_type, job_name))
    
    job = frappe.get_doc(job_type, job_name)
    if job.docstatus != 1:
        frappe.throw(_("{0} must be submitted to create Purchase Invoice.").format(job_type))
    
    config = CHARGE_CONFIG.get(job_type)
    if not config:
        frappe.throw(_("Purchase Invoice creation not supported for {0}.").format(job_type))
    
    charges_field, cost_field, rate_field, qty_field, item_field, supplier_field = config
    charges = list(job.get(charges_field) or [])
    
    # Filter charges with cost > 0
    cost_rows = []
    for ch in charges:
        cost = flt(
            getattr(ch, cost_field, None)
            or (flt(getattr(ch, rate_field, 0)) * flt(getattr(ch, qty_field or "quantity", 1) or 1)),
            0,
        )
        if cost <= 0:
            continue
        item_code = getattr(ch, item_field, None)
        if not item_code:
            continue
        sup = getattr(ch, supplier_field, None) if supplier_field else None
        cost_rows.append((ch, cost, item_code, sup))
    
    if not cost_rows:
        frappe.throw(_("No charges with cost amount found in {0}.").format(job_type))
    
    # Resolve supplier: from first row with pay_to, or argument, or settings
    resolved_supplier = supplier
    for _, _, _, sup in cost_rows:
        if sup:
            resolved_supplier = sup
            break
    if not resolved_supplier:
        resolved_supplier = frappe.db.get_single_value("Logistics Settings", "default_cost_supplier")
    if not resolved_supplier:
        frappe.throw(_("Supplier is required. Set pay_to on charges or pass supplier or configure default_cost_supplier in Logistics Settings."))
    
    # Create Purchase Invoice
    pi = frappe.new_doc("Purchase Invoice")
    pi.supplier = resolved_supplier
    pi.company = job.company
    pi.posting_date = posting_date or today()
    
    if getattr(job, "branch", None):
        pi.branch = job.branch
    if getattr(job, "cost_center", None):
        pi.cost_center = job.cost_center
    if getattr(job, "profit_center", None):
        pi.profit_center = job.profit_center
    
    # Set reference to job (custom fields)
    pi_meta = frappe.get_meta("Purchase Invoice")
    if pi_meta.get_field("reference_doctype"):
        pi.reference_doctype = job_type
        pi.reference_name = job_name
    
    base_remarks = pi.remarks or ""
    note = _("Auto-created from {0} {1}").format(job_type, job_name)
    pi.remarks = f"{base_remarks}\n{note}" if base_remarks else note
    
    pi_item_meta = frappe.get_meta("Purchase Invoice Item")
    has_ref = pi_item_meta.get_field("reference_doctype") and pi_item_meta.get_field("reference_name")
    
    for ch, cost, item_code, _sup in cost_rows:
        qty = flt(getattr(ch, qty_field or "quantity", 1) or 1)
        if qty <= 0:
            qty = 1
        rate = cost / qty
        row = pi.append("items", {
            "item_code": item_code,
            "qty": qty,
            "rate": rate,
        })
        if has_ref:
            row.reference_doctype = job_type
            row.reference_name = job_name
    
    pi.set_missing_values()
    pi.insert(ignore_permissions=True)
    
    # Update job
    frappe.db.set_value(job_type, job_name, "purchase_invoice", pi.name, update_modified=False)
    frappe.db.set_value(job_type, job_name, "date_purchase_invoice_requested", pi.posting_date, update_modified=False)
    
    return {
        "ok": True,
        "message": _("Purchase Invoice {0} created successfully.").format(pi.name),
        "purchase_invoice": pi.name,
    }
