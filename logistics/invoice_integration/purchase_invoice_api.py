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
import json

JOB_DOCTYPES = ("Transport Job", "Air Shipment", "Sea Shipment", "Warehouse Job", "Declaration")

# Child table doctype for charges (used to tag rows as Requested)
CHARGES_CHILD_DOCTYPE = {
    "Transport Job": "Transport Job Charges",
    "Air Shipment": "Air Shipment Charges",
    "Sea Shipment": "Sea Shipment Charges",
    "Warehouse Job": "Warehouse Job Charges",
    "Declaration": "Declaration Charges",
}

# Charge table and cost field mapping: (charges_field, cost_field, rate_field, qty_field, item_field, supplier_field)
CHARGE_CONFIG = {
    "Transport Job": ("charges", "estimated_cost", "unit_cost", "quantity", "item_code", "pay_to"),
    "Air Shipment": ("charges", "estimated_cost", "estimated_cost", "quantity", "item_code", "pay_to"),
    # Sea Shipment Charges: estimated_cost / unit_cost * cost_quantity (no buying_amount field)
    "Sea Shipment": ("charges", "estimated_cost", "unit_cost", "cost_quantity", "charge_item", "pay_to"),
    "Warehouse Job": ("charges", "total", "rate", "quantity", "item_code", None),
    "Declaration": ("charges", "estimated_cost", "unit_cost", "quantity", "item_code", None),
}

# Statuses that mean the charge is already in a PI or further along - exclude from eligibility (avoid duplicate posting)
PI_EXCLUDED_STATUSES = ("Requested", "Invoiced", "Posted", "Paid")


def _sea_shipment_row_cost(ch) -> float:
    """Sea Shipment Charges: actual_cost when > 0, else estimated_cost, else unit_cost * cost_quantity, else cost_base_amount."""
    c = flt(getattr(ch, "actual_cost", None) or 0)
    if c <= 0:
        c = flt(getattr(ch, "estimated_cost", None) or 0)
    if c > 0:
        return c
    u = flt(getattr(ch, "unit_cost", 0))
    q = flt(getattr(ch, "cost_quantity", None) or getattr(ch, "quantity", 1) or 1)
    if u * q > 0:
        return u * q
    return flt(getattr(ch, "cost_base_amount", None) or 0)


def _get_eligible_cost_rows(job, config):
    """Build list of (index, ch, cost, item_code, pay_to) for charges with cost > 0, item set, and not already requested/posted/paid."""
    charges_field, cost_field, rate_field, qty_field, item_field, supplier_field = config
    charges = list(job.get(charges_field) or [])
    rows = []
    for idx, ch in enumerate(charges):
        status = getattr(ch, "purchase_invoice_status", None)
        if status in PI_EXCLUDED_STATUSES or getattr(ch, "purchase_invoice", None):
            continue
        if job.doctype == "Sea Shipment":
            cost = _sea_shipment_row_cost(ch)
        else:
            # Use actual_cost for PI when present and > 0, else estimated/cost_field
            cost = flt(getattr(ch, "actual_cost", None) or 0)
            if cost <= 0:
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
        rows.append((idx, ch, cost, item_code, sup))
    return rows


@frappe.whitelist()
def get_eligible_charges_for_purchase_invoice(job_type: str, job_name: str) -> Dict[str, Any]:
    """
    Return list of eligible charges for PI creation so the user can select which to include.
    Used by the Create Purchase Invoice dialog.
    """
    if job_type not in JOB_DOCTYPES:
        frappe.throw(_("Invalid job type: {0}").format(job_type))
    if not frappe.db.exists(job_type, job_name):
        frappe.throw(_("{0} {1} does not exist.").format(job_type, job_name))
    job = frappe.get_doc(job_type, job_name)
    config = CHARGE_CONFIG.get(job_type)
    if not config:
        frappe.throw(_("Purchase Invoice creation not supported for {0}.").format(job_type))

    charges_field, cost_field, rate_field, qty_field, item_field, supplier_field = config
    cost_rows = _get_eligible_cost_rows(job, config)
    if not cost_rows:
        return {
            "eligible_charges": [],
            "default_supplier": None,
            "default_posting_date": today(),
            "company": job.company,
        }

    # Build list for dialog: use position in cost_rows as the index we pass back (0, 1, 2, ...)
    # Invoice uses qty=1 with estimated cost as unit rate
    eligible = []
    default_supplier = None
    for row_idx, (doc_idx, ch, cost, item_code, sup) in enumerate(cost_rows):
        item_name = frappe.db.get_value("Item", item_code, "item_name") or item_code
        if sup and default_supplier is None:
            default_supplier = sup
        eligible.append({
            "index": row_idx,
            "item_code": item_code,
            "item_name": item_name,
            "cost": cost,
            "quantity": 1,
            "pay_to": sup,
        })
    if not default_supplier:
        default_supplier = frappe.db.get_single_value("Logistics Settings", "default_cost_supplier")
    return {
        "eligible_charges": eligible,
        "default_supplier": default_supplier,
        "default_posting_date": today(),
        "company": job.company,
    }


@frappe.whitelist()
def create_purchase_invoice(
    job_type: str,
    job_name: str,
    supplier: Optional[str] = None,
    posting_date: Optional[str] = None,
    due_date: Optional[str] = None,
    bill_no: Optional[str] = None,
    bill_date: Optional[str] = None,
    selected_charge_indices: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create Purchase Invoice from job/shipment costs.

    Args:
        job_type: Transport Job, Air Shipment, Sea Shipment, Warehouse Job, or Declaration
        job_name: Name of the job document
        supplier: Optional default supplier (used when charges have no pay_to)
        posting_date: Optional posting date (default: today)
        due_date: Optional due date for the Purchase Invoice
        bill_no: Optional supplier bill / reference number
        bill_date: Optional supplier bill date
        selected_charge_indices: Optional JSON list of integers (indices into eligible charges).
            If provided, only these charges are included; otherwise all eligible charges are included.

    Returns:
        dict with ok, message, purchase_invoice
    """
    if job_type not in JOB_DOCTYPES:
        frappe.throw(_("Invalid job type: {0}").format(job_type))

    if not frappe.db.exists(job_type, job_name):
        frappe.throw(_("{0} {1} does not exist.").format(job_type, job_name))

    job = frappe.get_doc(job_type, job_name)
    config = CHARGE_CONFIG.get(job_type)
    if not config:
        frappe.throw(_("Purchase Invoice creation not supported for {0}.").format(job_type))

    charges_field, cost_field, rate_field, qty_field, item_field, supplier_field = config
    cost_rows_raw = _get_eligible_cost_rows(job, config)
    # cost_rows_raw: list of (doc_idx, ch, cost, item_code, sup)

    if not cost_rows_raw:
        frappe.throw(_("No charges with cost amount found in {0}.").format(job_type))

    # Filter by selected indices if provided (indices are 0-based into cost_rows_raw)
    if selected_charge_indices is not None:
        try:
            indices = json.loads(selected_charge_indices) if isinstance(selected_charge_indices, str) else selected_charge_indices
            indices = [int(x) for x in indices]
            cost_rows = [cost_rows_raw[i] for i in indices if 0 <= i < len(cost_rows_raw)]
        except (TypeError, ValueError, IndexError):
            cost_rows = cost_rows_raw
    else:
        cost_rows = cost_rows_raw

    if not cost_rows:
        frappe.throw(_("No charges selected for Purchase Invoice."))

    # Resolve supplier: from first row with pay_to, or argument, or settings
    resolved_supplier = supplier
    for _doc_idx, _ch, _cost, _item_code, sup in cost_rows:
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
    if due_date:
        pi.due_date = due_date
    if bill_no:
        pi.bill_no = bill_no
    if bill_date:
        pi.bill_date = bill_date

    # Copy accounting dimensions only when both job and PI have the field (design §4.2)
    pi_meta = frappe.get_meta("Purchase Invoice")
    for dim in ("branch", "cost_center", "profit_center", "project"):
        if pi_meta.get_field(dim) and getattr(job, dim, None):
            setattr(pi, dim, getattr(job, dim))

    # Set reference to job (custom fields)
    if pi_meta.get_field("reference_doctype"):
        pi.reference_doctype = job_type
        pi.reference_name = job_name
    # Job costing number for GL/profitability (design §6.3)
    if pi_meta.get_field("job_costing_number") and getattr(job, "job_costing_number", None):
        pi.job_costing_number = job.job_costing_number

    base_remarks = pi.remarks or ""
    note = _("Auto-created from {0} {1}").format(job_type, job_name)
    pi.remarks = f"{base_remarks}\n{note}" if base_remarks else note

    pi_item_meta = frappe.get_meta("Purchase Invoice Item")
    has_ref = pi_item_meta.get_field("reference_doctype") and pi_item_meta.get_field("reference_name")

    for _doc_idx, ch, cost, item_code, _sup in cost_rows:
        # Quantity = 1, estimated cost as unit rate
        item_payload = {
            "item_code": item_code,
            "qty": 1,
            "rate": cost,
        }
        # Description: include Calc Notes (cost_calc_notes or calculation_notes)
        calc_notes = getattr(ch, "cost_calc_notes", None) or getattr(ch, "calculation_notes", None)
        if calc_notes:
            item_payload["description"] = calc_notes
        row = pi.append("items", item_payload)
        if has_ref:
            row.reference_doctype = job_type
            row.reference_name = job_name

    pi.set_missing_values()
    pi.insert(ignore_permissions=True)

    # Update job
    frappe.db.set_value(job_type, job_name, "purchase_invoice", pi.name, update_modified=False)
    frappe.db.set_value(job_type, job_name, "date_purchase_invoice_requested", pi.posting_date, update_modified=False)

    # Tag selected charge rows as Requested (so they become read-only)
    child_doctype = CHARGES_CHILD_DOCTYPE.get(job_type)
    if child_doctype and frappe.db.table_exists(child_doctype):
        child_meta = frappe.get_meta(child_doctype)
        if child_meta.get_field("purchase_invoice_status"):
            for _doc_idx, ch, cost, item_code, _sup in cost_rows:
                ch_name = getattr(ch, "name", None)
                if ch_name and not (isinstance(ch_name, str) and ch_name.startswith("new")):
                    frappe.db.set_value(
                        child_doctype,
                        ch_name,
                        {
                            "purchase_invoice_status": "Requested",
                            "purchase_invoice": pi.name,
                        },
                        update_modified=False,
                    )
            frappe.db.commit()

    return {
        "ok": True,
        "message": _("Purchase Invoice {0} created successfully.").format(pi.name),
        "purchase_invoice": pi.name,
    }
