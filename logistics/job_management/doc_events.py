"""
Document event handlers for Recognition Engine integration

These handlers integrate the recognition engine with job document lifecycle events.
"""

import frappe
from frappe.utils import flt, cint

from logistics.job_management.recognition_engine import (
    get_charge_row_cost_amount,
    get_charge_row_selling_amount,
)


def on_job_validate_estimates(doc, method=None):
    """Persist header estimated revenue/costs from charge lines (validate runs before DB write)."""
    update_estimates_from_charges(doc)
    # Draft only: after submit these fields are not allow_on_submit. Auto-recognize
    # syncs in-memory and stamps via _save_job (ignore_validate_update_after_submit).
    if cint(getattr(doc, "docstatus", 0)) != 0:
        return
    try:
        from logistics.job_management.recognition_engine import sync_job_recognition_fields_from_policy

        sync_job_recognition_fields_from_policy(doc)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "sync_job_recognition_fields_from_policy")


def on_job_update(doc, method):
    """
    Handle job document updates.
    
    - Recalculate estimated revenue/costs from charges
    - Handle job closure (close WIP and accruals)
    """
    # Recalculate estimates from charges
    update_estimates_from_charges(doc)
    
    # Check for job closure
    handle_job_closure(doc)


def on_job_submit(doc, method=None):
    """
    Handle job submission.

    Enqueue auto-recognition when Recognition Policy Settings has Auto Recognize
    enabled. Does not post inline (missing ATA/ATD must not block submit).
    """
    from logistics.job_management.auto_recognition import enqueue_auto_recognize

    enqueue_auto_recognize(doc, method)


def update_estimates_from_charges(doc):
    """Update estimated revenue and costs from charges table."""
    charges_table = get_charges_table_name(doc.doctype)

    if not charges_table or not hasattr(doc, charges_table):
        return

    total_revenue = 0
    total_cost = 0

    for charge in doc.get(charges_table, []):
        total_revenue += get_charge_row_selling_amount(charge)
        total_cost += get_charge_row_cost_amount(charge)

    if hasattr(doc, "estimated_revenue"):
        doc.estimated_revenue = total_revenue

    if hasattr(doc, "estimated_costs"):
        doc.estimated_costs = total_cost


def handle_job_closure(doc):
    """Handle job closure - close WIP and accruals if job is closed."""
    closed_statuses = ["Closed", "Completed", "Cancelled"]
    
    if not hasattr(doc, 'status'):
        return
    
    if doc.status not in closed_statuses:
        return
    
    # Check if there's anything to close
    if flt(doc.get("wip_amount", 0)) <= 0 and flt(doc.get("accrual_amount", 0)) <= 0:
        return
    
    # Close recognition
    from logistics.job_management.recognition_engine import RecognitionEngine
    
    engine = RecognitionEngine(doc)
    
    if flt(doc.get("wip_amount", 0)) > 0:
        engine.close_wip()
    
    if flt(doc.get("accrual_amount", 0)) > 0:
        engine.close_accruals()


def get_charges_table_name(doctype):
    """Get the charges child table fieldname for a doctype."""
    charges_tables = {
        "Air Shipment": "charges",
        "Sea Shipment": "charges",
        "Transport Job": "charges",
        "Warehouse Job": "charges",
        "Declaration": "charges",
        "General Job": "charges",
        "Project Job": "charges",
        "Special Project": "charges",
        "Docket": "charges",
    }
    return charges_tables.get(doctype)


# Scheduler job for period closing
def process_recognition_adjustments():
    """
    Scheduled job to process recognition adjustments.
    
    This can be configured to run at period end.
    """
    from logistics.job_management.recognition_engine import process_period_closing_adjustments
    
    companies = frappe.get_all("Company", pluck="name")
    
    for company in companies:
        try:
            # Use today as period end for automated processing
            result = process_period_closing_adjustments(company, frappe.utils.nowdate())
            
            if result.get("wip_adjustments") or result.get("accrual_adjustments"):
                frappe.log_error(
                    message=f"Recognition adjustments processed for {company}: {result}",
                    title="Recognition Adjustments Processed"
                )
                
        except Exception as e:
            frappe.log_error(
                message=str(e),
                title=f"Recognition Adjustment Error: {company}"
            )
