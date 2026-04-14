"""
Document event handlers for Recognition Engine integration

These handlers integrate the recognition engine with job document lifecycle events.
"""

import frappe
from frappe import _
from frappe.utils import flt

from logistics.job_management.recognition_engine import (
    get_charge_row_cost_amount,
    get_charge_row_selling_amount,
)


def on_job_validate_estimates(doc, method=None):
    """Persist header estimated revenue/costs from charge lines (validate runs before DB write)."""
    update_estimates_from_charges(doc)


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
    
    Auto-recognize WIP and accruals based on Recognition Policy Settings.
    Runs when enable_wip_recognition or enable_accrual_recognition is enabled.
    """
    from logistics.job_management.recognition_engine import RecognitionEngine, get_recognition_settings

    settings = get_recognition_settings(doc)
    if not settings.get("enable_wip_recognition") and not settings.get("enable_accrual_recognition"):
        return

    engine = RecognitionEngine(doc)
    recognition_date = None

    if settings.get("enable_wip_recognition"):
        try:
            wip_je = engine.recognize_wip(recognition_date)
            if wip_je:
                frappe.msgprint(_("WIP recognized: {0}").format(wip_je), indicator="green")
        except Exception as e:
            frappe.log_error(str(e), "Recognition - WIP on Submit")
            frappe.throw(_("WIP recognition failed: {0}").format(str(e)))

    if settings.get("enable_accrual_recognition"):
        doc.reload()
        engine = RecognitionEngine(doc)
        try:
            accrual_je = engine.recognize_accruals(recognition_date)
            if accrual_je:
                frappe.msgprint(_("Accruals recognized: {0}").format(accrual_je), indicator="green")
        except Exception as e:
            frappe.log_error(str(e), "Recognition - Accrual on Submit")
            frappe.throw(_("Accrual recognition failed: {0}").format(str(e)))


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
