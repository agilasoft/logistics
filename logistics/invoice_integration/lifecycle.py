# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Invoice lifecycle integration: update job/shipment status when Sales Invoice or
Purchase Invoice is submitted, paid, or cancelled.
"""

import frappe
from frappe import _
from frappe.utils import getdate, today, flt

# Job doctypes that have invoice monitoring fields
JOB_DOCTYPES = ("Transport Job", "Air Shipment", "Sea Shipment", "Warehouse Job", "Declaration")

# Fields to update on jobs
SI_LIFECYCLE_FIELDS = (
    "sales_invoice",
    "fully_invoiced",
    "date_fully_invoiced",
    "fully_paid",
    "date_fully_paid",
    "date_sales_invoice_requested",
    "date_sales_invoice_submitted",
)
PI_LIFECYCLE_FIELDS = (
    "purchase_invoice",
    "costs_fully_paid",
    "date_costs_fully_paid",
    "date_purchase_invoice_requested",
    "date_purchase_invoice_submitted",
)


def get_jobs_linked_to_sales_invoice(si_name: str) -> list:
    """Get jobs/shipments linked to this Sales Invoice."""
    jobs = []
    # 1. Via sales_invoice field on job
    for dt in JOB_DOCTYPES:
        if not frappe.db.table_exists(dt):
            continue
        meta = frappe.get_meta(dt)
        if "sales_invoice" not in [f.fieldname for f in meta.fields]:
            continue
        names = frappe.get_all(
            dt,
            filters={"sales_invoice": si_name, "docstatus": ["!=", 2]},
            pluck="name",
        )
        for n in names:
            jobs.append((dt, n))
    # 2. Via reference_doctype/reference_name on SI Item
    items = frappe.get_all(
        "Sales Invoice Item",
        filters={"parent": si_name, "parenttype": "Sales Invoice"},
        fields=["reference_doctype", "reference_name"],
    )
    for row in items:
        if row.get("reference_doctype") and row.get("reference_name"):
            if row.reference_doctype in JOB_DOCTYPES and frappe.db.exists(
                row.reference_doctype, row.reference_name
            ):
                jobs.append((row.reference_doctype, row.reference_name))
    return list(set(jobs))


def get_jobs_linked_to_purchase_invoice(pi_name: str) -> list:
    """Get jobs/shipments linked to this Purchase Invoice."""
    jobs = []
    # 1. Via purchase_invoice field on job
    for dt in JOB_DOCTYPES:
        if not frappe.db.table_exists(dt):
            continue
        meta = frappe.get_meta(dt)
        if "purchase_invoice" not in [f.fieldname for f in meta.fields]:
            continue
        names = frappe.get_all(
            dt,
            filters={"purchase_invoice": pi_name, "docstatus": ["!=", 2]},
            pluck="name",
        )
        for n in names:
            jobs.append((dt, n))
    # 2. Via reference_doctype/reference_name on PI header or PI Item
    ref_dt = frappe.db.get_value("Purchase Invoice", pi_name, "reference_doctype")
    ref_name = frappe.db.get_value("Purchase Invoice", pi_name, "reference_name")
    if ref_dt and ref_name and ref_dt in JOB_DOCTYPES:
        jobs.append((ref_dt, ref_name))
    return list(set(jobs))


def update_job_on_sales_invoice_submit(si_doc):
    """Update linked jobs when Sales Invoice is submitted."""
    jobs = get_jobs_linked_to_sales_invoice(si_doc.name)
    posting_date = getdate(si_doc.posting_date)
    grand_total = flt(si_doc.grand_total)
    for job_dt, job_name in jobs:
        try:
            updates = {
                "sales_invoice": si_doc.name,
                "date_sales_invoice_submitted": posting_date,
            }
            # Set requested date if not yet set
            job = frappe.get_doc(job_dt, job_name)
            if not job.get("date_sales_invoice_requested"):
                updates["date_sales_invoice_requested"] = posting_date
            # Check if fully invoiced (simplified: if this is the only/last SI)
            total_revenue = _get_estimated_revenue(job)
            if total_revenue and grand_total >= total_revenue * 0.99:
                updates["fully_invoiced"] = 1
                updates["date_fully_invoiced"] = posting_date
            for k, v in updates.items():
                if _has_field(job_dt, k):
                    frappe.db.set_value(job_dt, job_name, k, v, update_modified=False)
        except Exception as e:
            frappe.log_error(
                f"Failed to update {job_dt} {job_name} on SI submit: {e}",
                "Invoice Integration Error",
            )
    if jobs:
        frappe.db.commit()


def update_job_on_sales_invoice_cancel(si_doc):
    """Clear links and reset statuses when Sales Invoice is cancelled."""
    jobs = get_jobs_linked_to_sales_invoice(si_doc.name)
    for job_dt, job_name in jobs:
        try:
            updates = {
                "sales_invoice": None,
                "fully_invoiced": 0,
                "date_fully_invoiced": None,
                "fully_paid": 0,
                "date_fully_paid": None,
                "date_sales_invoice_requested": None,
                "date_sales_invoice_submitted": None,
            }
            for k, v in updates.items():
                if _has_field(job_dt, k):
                    frappe.db.set_value(job_dt, job_name, k, v, update_modified=False)
        except Exception as e:
            frappe.log_error(
                f"Failed to update {job_dt} {job_name} on SI cancel: {e}",
                "Invoice Integration Error",
            )
    if jobs:
        frappe.db.commit()


def update_job_on_purchase_invoice_submit(pi_doc):
    """Update linked jobs when Purchase Invoice is submitted."""
    jobs = get_jobs_linked_to_purchase_invoice(pi_doc.name)
    posting_date = getdate(pi_doc.posting_date)
    for job_dt, job_name in jobs:
        try:
            updates = {
                "purchase_invoice": pi_doc.name,
                "date_purchase_invoice_submitted": posting_date,
            }
            job = frappe.get_doc(job_dt, job_name)
            if not job.get("date_purchase_invoice_requested"):
                updates["date_purchase_invoice_requested"] = posting_date
            for k, v in updates.items():
                if _has_field(job_dt, k):
                    frappe.db.set_value(job_dt, job_name, k, v, update_modified=False)
        except Exception as e:
            frappe.log_error(
                f"Failed to update {job_dt} {job_name} on PI submit: {e}",
                "Invoice Integration Error",
            )
    if jobs:
        frappe.db.commit()


def update_job_on_purchase_invoice_cancel(pi_doc):
    """Clear links and reset statuses when Purchase Invoice is cancelled."""
    jobs = get_jobs_linked_to_purchase_invoice(pi_doc.name)
    for job_dt, job_name in jobs:
        try:
            updates = {
                "purchase_invoice": None,
                "costs_fully_paid": 0,
                "date_costs_fully_paid": None,
                "date_purchase_invoice_requested": None,
                "date_purchase_invoice_submitted": None,
            }
            for k, v in updates.items():
                if _has_field(job_dt, k):
                    frappe.db.set_value(job_dt, job_name, k, v, update_modified=False)
        except Exception as e:
            frappe.log_error(
                f"Failed to update {job_dt} {job_name} on PI cancel: {e}",
                "Invoice Integration Error",
            )
    if jobs:
        frappe.db.commit()


def update_job_on_payment(party_type: str, party: str):
    """Update fully_paid when Sales Invoice or Purchase Invoice is fully paid."""
    if party_type == "Customer":
        # Find SIs for this customer with outstanding = 0
        sis = frappe.get_all(
            "Sales Invoice",
            filters={
                "customer": party,
                "docstatus": 1,
                "outstanding_amount": 0,
            },
            pluck="name",
        )
        for si_name in sis:
            jobs = get_jobs_linked_to_sales_invoice(si_name)
            for job_dt, job_name in jobs:
                if _has_field(job_dt, "fully_paid"):
                    frappe.db.set_value(
                        job_dt, job_name,
                        "fully_paid", 1,
                        update_modified=False,
                    )
                if _has_field(job_dt, "date_fully_paid"):
                    frappe.db.set_value(
                        job_dt, job_name,
                        "date_fully_paid", today(),
                        update_modified=False,
                    )
    elif party_type == "Supplier":
        pis = frappe.get_all(
            "Purchase Invoice",
            filters={
                "supplier": party,
                "docstatus": 1,
                "outstanding_amount": 0,
            },
            pluck="name",
        )
        for pi_name in pis:
            jobs = get_jobs_linked_to_purchase_invoice(pi_name)
            for job_dt, job_name in jobs:
                if _has_field(job_dt, "costs_fully_paid"):
                    frappe.db.set_value(
                        job_dt, job_name,
                        "costs_fully_paid", 1,
                        update_modified=False,
                    )
                if _has_field(job_dt, "date_costs_fully_paid"):
                    frappe.db.set_value(
                        job_dt, job_name,
                        "date_costs_fully_paid", today(),
                        update_modified=False,
                    )


def _has_field(doctype: str, fieldname: str) -> bool:
    """Check if doctype has the field."""
    try:
        meta = frappe.get_meta(doctype)
        return bool(meta.get_field(fieldname))
    except Exception:
        return False


def _get_estimated_revenue(job) -> float:
    """Get estimated revenue from job charges."""
    total = 0
    charges_field = _get_charges_field(job.doctype)
    if not charges_field:
        return 0
    for row in job.get(charges_field) or []:
        amt = flt(
            getattr(row, "estimated_revenue", None)
            or getattr(row, "unit_rate", None) * flt(getattr(row, "quantity", 1))
            or getattr(row, "selling_amount", None)
            or getattr(row, "rate", None) * flt(getattr(row, "quantity", 1))
            or getattr(row, "total", None),
            0,
        )
        total += amt
    return total


def _get_charges_field(doctype: str) -> str:
    """Get the charges child table field name for a job doctype."""
    mapping = {
        "Transport Job": "charges",
        "Air Shipment": "charges",
        "Sea Shipment": "charges",
        "Warehouse Job": "charges",
        "Declaration": "charges",
    }
    return mapping.get(doctype, "charges")
