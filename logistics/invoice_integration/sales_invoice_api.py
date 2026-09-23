# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Create Sales Invoice from logistics job/shipment with dialog: header details and charge selection.
Charges are pre-filtered by header (e.g. customer/bill_to, invoice_type).
"""

import frappe
from frappe import _
from frappe.model.naming import get_default_naming_series, make_autoname, set_name_by_naming_series
from frappe.utils import flt, today
from typing import Dict, Any, Optional, List
import json

from logistics.job_management.recognition_engine import resolve_charge_row_selling
from logistics.utils.freight_95_5 import (
    apply_freight_95_post_missing_values,
    build_sales_invoice_item_payloads_for_charge,
    resolve_sales_invoice_line_qty_rate,
)
from logistics.special_projects.special_project_si_job_number import (
    resolve_job_number_for_special_project_charge,
)
from logistics.invoice_integration.billing_currency import (
    charge_to_company_rate_selling,
    company_currency as _company_currency,
    convert_amount_to_billing_currency as _convert_charge_amount_to_billing_currency,
    customer_default_billing_currency as _get_customer_default_billing_currency,
    invoice_billing_context as _si_billing_context,
    resolve_selling_charge_currency as _resolve_charge_currency,
)


def ensure_sales_invoice_name_for_server_insert(si) -> None:
    """
    Sales Invoice may use autoname 'prompt', which requires a name before insert.
    When creating from the server, derive the name from naming_series (including
    Invoice Type / DocType default) or fall back to a hash id if no series exists.
    """
    if getattr(si, "name", None):
        return
    meta = frappe.get_meta("Sales Invoice")
    autoname = (meta.autoname or "").lower()
    if not autoname.startswith("prompt"):
        return
    if si.naming_series or get_default_naming_series("Sales Invoice"):
        set_name_by_naming_series(si)
    else:
        si.name = make_autoname("hash", "Sales Invoice")


def job_dimension_link_field_writable(field) -> bool:
    """Allow writing only if a Link field's target DocType exists (legacy options e.g. Job Costing Number)."""
    if not field:
        return False
    if field.fieldtype != "Link":
        return True
    opt = (field.options or "").strip()
    if not opt:
        return True
    return bool(frappe.db.exists("DocType", opt))


SALES_JOB_DOCTYPES = (
    "Transport Job",
    "Air Shipment",
    "Sea Shipment",
    "Warehouse Job",
    "Declaration",
    "Special Project",
    "Docket",
)

# Child table doctype for charges (for tagging sales_invoice_status / sales_invoice)
SALES_CHARGES_CHILD_DOCTYPE = {
    "Transport Job": "Transport Job Charges",
    "Air Shipment": "Air Shipment Charges",
    "Sea Shipment": "Sea Shipment Charges",
    "Warehouse Job": "Warehouse Job Charges",
    "Declaration": "Declaration Charges",
    "Special Project": "Special Project Charges",
    "Docket": "MICE Project Charges",
}

# Statuses that mean the charge is already in an SI or further along - exclude from eligibility (avoid duplicate posting)
SI_EXCLUDED_STATUSES = ("Requested", "Posted", "Paid")

# (charges_field, revenue_field, rate_field, qty_field, item_field, item_name_field, bill_to_field, invoice_type_field)
# bill_to_field and invoice_type_field used to pre-filter when customer/invoice_type provided
SALES_CHARGE_CONFIG = {
    "Transport Job": ("charges", "estimated_revenue", "unit_rate", "quantity", "item_code", "item_name", "bill_to", None),
    "Air Shipment": ("charges", "estimated_revenue", "unit_rate", "quantity", "item_code", "item_name", None, "invoice_type"),
    # Sea Shipment currently uses item_code/item_name/estimated_revenue in child rows.
    # Keep downstream logic backward-compatible with legacy fields (charge_item/charge_name/selling_amount).
    "Sea Shipment": ("charges", "estimated_revenue", "unit_rate", "quantity", "item_code", "item_name", "bill_to", "invoice_type"),
    "Warehouse Job": ("charges", "estimated_revenue", "unit_rate", "quantity", "item_code", "item_name", None, None),
    "Declaration": ("charges", "estimated_revenue", "unit_rate", "quantity", "item_code", "item_name", None, None),
    # Special Project Charges mirror the operational doc shape (item_code, estimated_revenue, unit_rate, quantity, bill_to, invoice_type).
    "Special Project": ("charges", "estimated_revenue", "unit_rate", "quantity", "item_code", "item_name", "bill_to", "invoice_type"),
    # MICE Project Charges (used by Docket) share the same shape as Sea Shipment / Special Project.
    "Docket": ("charges", "estimated_revenue", "unit_rate", "quantity", "item_code", "item_name", "bill_to", "invoice_type"),
}


def _get_eligible_revenue_rows(job, config, customer=None, invoice_type=None):
    """Return list of (idx, ch, revenue, item_code, item_name, ...) for charges with revenue > 0, item set, not already requested/posted/paid.
    For Sea Shipment, filter by customer (bill_to) and invoice_type when provided.
    """
    charges_field, revenue_field, rate_field, qty_field, item_field, item_name_field, bill_to_field, invoice_type_field = config
    charges = list(job.get(charges_field) or [])
    rows = []
    for idx, ch in enumerate(charges):
        status = getattr(ch, "sales_invoice_status", None)
        if status in SI_EXCLUDED_STATUSES or getattr(ch, "sales_invoice", None):
            continue
        # Prefer calculated actual revenue (qty × rate), same basis as Purchase Invoice costs
        revenue = flt(resolve_charge_row_selling(ch, prefer_actual=True))
        if revenue <= 0:
            revenue = flt(
                getattr(ch, revenue_field, None)
                or (flt(getattr(ch, rate_field, 0)) * flt(getattr(ch, qty_field or "quantity", 1) or 1)),
                0,
            )
        if revenue <= 0:
            # Legacy fallback (especially for older Sea Shipment rows)
            revenue = flt(
                getattr(ch, "selling_amount", None)
                or getattr(ch, "base_amount", None)
                or getattr(ch, "estimated_revenue", None)
                or 0
            )
        if revenue <= 0:
            continue
        item_code = getattr(ch, item_field, None) or getattr(ch, "charge_item", None)
        if not item_code:
            continue
        # Pre-filter by header details (Sea Shipment: bill_to, invoice_type)
        if customer and bill_to_field:
            bill_to = getattr(ch, bill_to_field, None)
            # Empty bill_to: charge is not scoped to a customer (include for any selected customer)
            if bill_to and bill_to != customer:
                continue
        if invoice_type is not None and invoice_type_field:
            ch_inv_type = getattr(ch, invoice_type_field, None)
            if ch_inv_type != invoice_type:
                continue
        item_name = getattr(ch, item_name_field, None) or getattr(ch, "charge_name", None) or item_code
        rows.append((idx, ch, revenue, item_code, item_name))
    return rows


@frappe.whitelist()
def get_eligible_charges_for_sales_invoice(
    job_type: str,
    job_name: str,
    customer: Optional[str] = None,
    invoice_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return list of eligible revenue charges for SI creation, optionally pre-filtered by customer and invoice_type.
    Used by the Create Sales Invoice dialog.
    """
    if job_type not in SALES_JOB_DOCTYPES:
        frappe.throw(_("Invalid job type: {0}").format(job_type))
    if not frappe.db.exists(job_type, job_name):
        frappe.throw(_("{0} {1} does not exist.").format(job_type, job_name))
    job = frappe.get_doc(job_type, job_name)
    from logistics.utils.menu_permission import assert_create_from_source

    assert_create_from_source("Sales Invoice", source_doc=job)
    config = SALES_CHARGE_CONFIG.get(job_type)
    if not config:
        frappe.throw(_("Sales Invoice creation not supported for {0}.").format(job_type))

    # Default customer from job/shipment
    # Docket bills the exhibitor by default (the `customer` field on Docket is the account customer fetched from Exhibit).
    default_customer = (
        getattr(job, "local_customer", None)
        or getattr(job, "exhibitor", None)
        or getattr(job, "customer", None)
    )
    if not customer:
        customer = default_customer

    company_currency = _company_currency(job.company)
    default_billing_currency = _get_customer_default_billing_currency(customer, job.company)

    cost_rows = _get_eligible_revenue_rows(job, config, customer=customer, invoice_type=invoice_type)
    if not cost_rows:
        return {
            "eligible_charges": [],
            "default_customer": default_customer,
            "default_posting_date": today(),
            "company": job.company,
            "company_currency": company_currency,
            "default_billing_currency": default_billing_currency,
            "has_invoice_type": bool(config[7]),
        }

    eligible = []
    for row_idx, (doc_idx, ch, revenue, item_code, item_name) in enumerate(cost_rows):
        line_qty, line_rate, display_revenue = resolve_sales_invoice_line_qty_rate(
            ch, revenue, job.company
        )
        charge_currency = _resolve_charge_currency(ch, job_type, job.company)
        eligible.append({
            "index": row_idx,
            "item_code": item_code,
            "item_name": item_name,
            "revenue": display_revenue,
            "quantity": line_qty if line_qty is not None else 1,
            "rate": line_rate if line_rate is not None else display_revenue,
            "currency": charge_currency,
            "apply_95_5_rule": int(bool(getattr(ch, "apply_95_5_rule", 0))),
            "taxable_freight_item": getattr(ch, "taxable_freight_item", None),
        })
    return {
        "eligible_charges": eligible,
        "default_customer": default_customer or customer,
        "default_posting_date": today(),
        "company": job.company,
        "company_currency": company_currency,
        "default_billing_currency": default_billing_currency,
        "has_invoice_type": bool(config[7]),
    }


@frappe.whitelist()
def create_sales_invoice_from_job(
    job_type: str,
    job_name: str,
    customer: str,
    posting_date: Optional[str] = None,
    invoice_type: Optional[str] = None,
    tax_category: Optional[str] = None,
    selected_charge_indices: Optional[str] = None,
    billing_currency: Optional[str] = None,
    exchange_rate: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Create Sales Invoice from job/shipment with selected charges and header details.
    """
    if job_type not in SALES_JOB_DOCTYPES:
        frappe.throw(_("Invalid job type: {0}").format(job_type))
    if not frappe.db.exists(job_type, job_name):
        frappe.throw(_("{0} {1} does not exist.").format(job_type, job_name))
    if not customer:
        frappe.throw(_("Customer is required."))

    job = frappe.get_doc(job_type, job_name)
    from logistics.utils.menu_permission import assert_create_from_source

    assert_create_from_source("Sales Invoice", source_doc=job)
    config = SALES_CHARGE_CONFIG.get(job_type)
    if not config:
        frappe.throw(_("Sales Invoice creation not supported for {0}.").format(job_type))
    cost_rows_raw = _get_eligible_revenue_rows(job, config, customer=customer, invoice_type=invoice_type)
    if not cost_rows_raw:
        frappe.throw(_("No charges with revenue found for the selected customer and invoice type."))

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
        frappe.throw(_("No charges selected for Sales Invoice."))

    # Naming series from Invoice Type (Sea Shipment)
    naming_series = None
    if invoice_type and frappe.db.exists("Invoice Type", invoice_type):
        naming_series = frappe.db.get_value("Invoice Type", invoice_type, "naming_series")

    si = frappe.new_doc("Sales Invoice")
    si_meta = frappe.get_meta("Sales Invoice")
    si.customer = customer
    si.company = job.company
    si.posting_date = posting_date or today()

    billing_ctx = _si_billing_context(
        job.company,
        billing_currency,
        exchange_rate,
        si.posting_date,
    )
    si.currency = billing_ctx["billing_currency"]
    si.conversion_rate = billing_ctx["billing_exchange_rate"]
    si.ignore_pricing_rule = 1

    if tax_category:
        si.tax_category = tax_category
    if naming_series:
        si.naming_series = naming_series
    if invoice_type:
        if si_meta.get_field("invoice_type"):
            si.invoice_type = invoice_type
        if si_meta.get_field("custom_invoice_type"):
            si.custom_invoice_type = invoice_type
    for dim in ("branch", "cost_center", "profit_center", "project"):
        if getattr(job, dim, None):
            if si_meta.get_field(dim):
                setattr(si, dim, getattr(job, dim))
    # job_number (current dimension) and legacy job_costing_number on some sites / restores
    job_ref = getattr(job, "job_number", None) or getattr(job, "job_costing_number", None)
    if job_ref:
        f_jn = si_meta.get_field("job_number")
        if f_jn and job_dimension_link_field_writable(f_jn):
            si.job_number = job_ref
        f_jc = si_meta.get_field("job_costing_number")
        if f_jc and job_dimension_link_field_writable(f_jc):
            si.job_costing_number = job_ref
    if getattr(job, "sales_quote", None) and si_meta.get_field("quotation_no"):
        si.quotation_no = job.sales_quote

    base_remarks = si.remarks or ""
    note = _("Auto-created from {0} {1}").format(job_type, job_name)
    si.remarks = f"{base_remarks}\n{note}" if base_remarks else note

    si_item_meta = frappe.get_meta("Sales Invoice Item")
    has_ref = si_item_meta.get_field("reference_doctype") and si_item_meta.get_field("reference_name")

    freight_95_line_indices: List[int] = []
    company_currency = billing_ctx["company_currency"]
    billing_cur = billing_ctx["billing_currency"]
    billing_xr = billing_ctx["billing_exchange_rate"]

    for doc_idx, ch, revenue, item_code, item_name in cost_rows:
        calc_notes = getattr(ch, "revenue_calc_notes", None) or getattr(ch, "calculation_notes", None)
        desc_parts = []
        if getattr(ch, "description", None):
            desc_parts.append(ch.description)
        elif getattr(ch, "charge_description", None):
            desc_parts.append(ch.charge_description)
        if calc_notes:
            desc_parts.append(calc_notes)
        description = "\n".join(desc_parts) if desc_parts else None

        charge_currency = _resolve_charge_currency(ch, job_type, job.company)
        charge_to_company = charge_to_company_rate_selling(ch, charge_currency, company_currency, si.posting_date)

        line_qty, line_rate, revenue = resolve_sales_invoice_line_qty_rate(ch, revenue, job.company)
        revenue = _convert_charge_amount_to_billing_currency(
            revenue,
            charge_currency,
            billing_cur,
            company_currency,
            billing_xr,
            charge_to_company,
        )
        if line_rate is not None:
            line_rate = _convert_charge_amount_to_billing_currency(
                line_rate,
                charge_currency,
                billing_cur,
                company_currency,
                billing_xr,
                charge_to_company,
            )
        uom = getattr(ch, "uom", None) if line_qty is not None else None

        line_job_ref = job_ref
        if job_type == "Special Project":
            line_job_ref = resolve_job_number_for_special_project_charge(job, ch) or job_ref

        payloads, clear_rel = build_sales_invoice_item_payloads_for_charge(
            ch,
            flt(revenue),
            item_code=item_code,
            item_name=item_name,
            description=description,
            job_type=job_type,
            company=job.company,
            currency=billing_cur,
            cost_center=getattr(job, "cost_center", None),
            profit_center=getattr(job, "profit_center", None),
            job_ref=line_job_ref,
            si_item_meta=si_item_meta,
            reference_doctype=job_type if has_ref else None,
            reference_name=job_name if has_ref else None,
            line_qty=line_qty,
            line_rate=line_rate,
            uom=uom,
            project=getattr(job, "project", None),
        )
        start_idx = len(si.items)
        for p in payloads:
            si.append("items", p)
        for rel in clear_rel:
            freight_95_line_indices.append(start_idx + rel)

    si.set_missing_values()
    apply_freight_95_post_missing_values(si, freight_95_line_indices)
    ensure_sales_invoice_name_for_server_insert(si)
    si.insert(ignore_permissions=True)

    if frappe.get_meta(job_type).get_field("sales_invoice"):
        frappe.db.set_value(job_type, job_name, "sales_invoice", si.name, update_modified=False)
    if frappe.get_meta(job_type).get_field("date_sales_invoice_requested"):
        frappe.db.set_value(job_type, job_name, "date_sales_invoice_requested", si.posting_date, update_modified=False)

    # Tag selected charge rows as Requested (reference SI; avoid duplicate posting)
    child_doctype = SALES_CHARGES_CHILD_DOCTYPE.get(job_type)
    if child_doctype and frappe.db.table_exists(child_doctype):
        child_meta = frappe.get_meta(child_doctype)
        if child_meta.get_field("sales_invoice_status") and child_meta.get_field("sales_invoice"):
            for doc_idx, ch, revenue, item_code, item_name in cost_rows:
                ch_name = getattr(ch, "name", None)
                if ch_name and not (isinstance(ch_name, str) and ch_name.startswith("new")):
                    frappe.db.set_value(
                        child_doctype,
                        ch_name,
                        {
                            "sales_invoice_status": "Requested",
                            "sales_invoice": si.name,
                        },
                        update_modified=False,
                    )
            frappe.db.commit()

    return {
        "ok": True,
        "message": _("Sales Invoice {0} created successfully.").format(si.name),
        "sales_invoice": si.name,
    }
