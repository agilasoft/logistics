# -*- coding: utf-8 -*-
# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Automation helper functions for Transport module.
Provides auto-billing and auto-vehicle assignment functionality.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from typing import Optional, Dict, Any


def is_auto_billing_enabled() -> bool:
    """Check if auto-billing is enabled in Transport Settings."""
    try:
        settings = frappe.get_single("Transport Settings")
        return bool(getattr(settings, "enable_auto_billing", False))
    except Exception:
        return False


def is_auto_vehicle_assignment_enabled() -> bool:
    """Check if auto-vehicle assignment is enabled in Transport Settings."""
    try:
        settings = frappe.get_single("Transport Settings")
        return bool(getattr(settings, "enable_auto_vehicle_assignment", False))
    except Exception:
        return False


def auto_assign_vehicle_to_leg(leg_doc: Document) -> Optional[Dict[str, Any]]:
    """
    Automatically assign a vehicle to a Transport Leg if auto-assignment is enabled.
    
    Args:
        leg_doc: Transport Leg document
        
    Returns:
        Dict with assignment result or None if not enabled/failed
    """
    if not is_auto_vehicle_assignment_enabled():
        return None
    
    if not leg_doc or leg_doc.doctype != "Transport Leg":
        return None
    
    # Skip if leg already has a run sheet assigned
    if getattr(leg_doc, "run_sheet", None):
        return None
    
    try:
        # Find a suitable vehicle for this leg
        vehicle_type = getattr(leg_doc, "vehicle_type", None)
        if not vehicle_type:
            return None
        
        # Find available vehicles of the required type
        vehicles = frappe.db.sql("""
            SELECT name, vehicle_type
            FROM `tabTransport Vehicle`
            WHERE vehicle_type = %s
            AND status = 'Active'
            AND name NOT IN (
                SELECT vehicle
                FROM `tabRun Sheet`
                WHERE vehicle IS NOT NULL
                AND status IN ('Draft', 'Submitted', 'In Progress')
            )
            LIMIT 1
        """, (vehicle_type,), as_dict=True)
        
        if not vehicles:
            return None
        
        vehicle = vehicles[0]["name"]
        
        # DO NOT auto-group: Always create a new Run Sheet per leg
        # Grouping must be explicitly enabled via group_legs_in_one_runsheet on Transport Job
        # or consolidate_legs parameter in Transport Plan
        
        # Create new Run Sheet
        rs_doc = frappe.new_doc("Run Sheet")
        rs_doc.vehicle = vehicle
        rs_doc.vehicle_type = vehicle_type
        if run_date:
            rs_doc.run_date = run_date
        rs_doc.status = "Draft"
        rs_doc.append("legs", {
            "transport_leg": leg_doc.name
        })
        rs_doc.insert(ignore_permissions=True)
        
        leg_doc.run_sheet = rs_doc.name
        leg_doc.save(ignore_permissions=True)
        
        return {"run_sheet": rs_doc.name, "vehicle": vehicle, "action": "created_new"}
        
    except Exception as e:
        frappe.log_error(f"Error in auto_assign_vehicle_to_leg for leg {leg_doc.name}: {str(e)}", "Auto Vehicle Assignment Error")
        return None


def auto_bill_transport_job(job_doc: Document) -> Optional[Dict[str, Any]]:
    """
    Automatically create a Sales Invoice for a Transport Job when it's completed,
    if auto-billing is enabled.
    
    Args:
        job_doc: Transport Job document
        
    Returns:
        Dict with billing result or None if not enabled/failed
    """
    if not is_auto_billing_enabled():
        return None
    
    if not job_doc or job_doc.doctype != "Transport Job":
        return None
    
    # Only auto-bill when status changes to "Completed"
    if getattr(job_doc, "status", None) != "Completed":
        return None
    
    # Check if Sales Invoice already exists
    if getattr(job_doc, "sales_invoice", None):
        return None
    
    try:
        # Import the create_sales_invoice function from transport_job
        from logistics.transport.doctype.transport_job.transport_job import create_sales_invoice
        
        result = create_sales_invoice(job_doc.name)
        return result
        
    except Exception as e:
        frappe.log_error(f"Error in auto_bill_transport_job for job {job_doc.name}: {str(e)}", "Auto Billing Error")
        return None

