"""
Document event handlers for Recognition Engine integration

These handlers integrate the recognition engine with job document lifecycle events.
"""

import frappe
from frappe import _
from frappe.utils import flt


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


def on_job_submit(doc, method):
    """
    Handle job submission.
    
    Optionally auto-recognize WIP and accruals based on settings.
    """
    from logistics.job_management.recognition_engine import get_recognition_settings
    
    settings = get_recognition_settings(doc)
    
    # Auto-recognition is optional and controlled by settings
    # By default, recognition is manual
    pass


def update_estimates_from_charges(doc):
    """Update estimated revenue and costs from charges table."""
    charges_table = get_charges_table_name(doc.doctype)
    
    if not charges_table or not hasattr(doc, charges_table):
        return
    
    total_revenue = 0
    total_cost = 0
    
    for charge in doc.get(charges_table, []):
        if hasattr(charge, 'estimated_revenue'):
            total_revenue += flt(charge.estimated_revenue)
        elif hasattr(charge, 'amount'):
            total_revenue += flt(charge.amount)
        
        if hasattr(charge, 'estimated_cost'):
            total_cost += flt(charge.estimated_cost)
        elif hasattr(charge, 'cost'):
            total_cost += flt(charge.cost)
    
    if hasattr(doc, 'estimated_revenue'):
        doc.estimated_revenue = total_revenue
    
    if hasattr(doc, 'estimated_costs'):
        doc.estimated_costs = total_cost


def handle_job_closure(doc):
    """Handle job closure - close WIP and accruals if job is closed."""
    closed_statuses = ["Closed", "Completed", "Cancelled"]
    
    if not hasattr(doc, 'status'):
        return
    
    if doc.status not in closed_statuses:
        return
    
    # Check if already closed
    if doc.get("wip_closed") and doc.get("accrual_closed"):
        return
    
    # Check if there's anything to close
    if flt(doc.get("wip_amount", 0)) <= 0 and flt(doc.get("accrual_amount", 0)) <= 0:
        return
    
    # Close recognition
    from logistics.job_management.recognition_engine import RecognitionEngine
    
    engine = RecognitionEngine(doc)
    
    if flt(doc.get("wip_amount", 0)) > 0 and not doc.get("wip_closed"):
        engine.close_wip()
    
    if flt(doc.get("accrual_amount", 0)) > 0 and not doc.get("accrual_closed"):
        engine.close_accruals()


def get_charges_table_name(doctype):
    """Get the charges child table fieldname for a doctype."""
    charges_tables = {
        "Air Shipment": "charges",
        "Sea Shipment": "charges",
        "Transport Job": "charges",
        "Warehouse Job": "charges",
        "Declaration": "charges",
        "General Job": "charges"
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
