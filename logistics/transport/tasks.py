# -*- coding: utf-8 -*-
# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Scheduled Tasks for Transport Module
"""

from __future__ import unicode_literals
from datetime import datetime, timedelta
import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime, cint


def update_transport_job_statuses():
    """
    Automatically update Transport Job statuses based on leg statuses.
    This runs periodically to ensure statuses are always in sync.
    Runs every 15 minutes via cron scheduler.
    """
    try:
        # Get all submitted Transport Jobs that might need status updates
        # Focus on jobs that are not Completed or Cancelled (these don't change)
        # Also exclude cancelled documents (docstatus = 2)
        jobs = frappe.get_all(
            "Transport Job",
            filters={
                "docstatus": 1,  # Only submitted jobs (not cancelled)
                "status": ["not in", ["Completed", "Cancelled"]]
            },
            fields=["name", "status"],
            limit=500  # Process in batches
        )
        
        if not jobs:
            return
        
        updated_count = 0
        error_count = 0
        
        for job_data in jobs:
            try:
                job_doc = frappe.get_doc("Transport Job", job_data.name)
                old_status = job_doc.status
                
                # Call update_status to recalculate based on current leg statuses
                job_doc.update_status()
                new_status = job_doc.status
                
                # Only update if status actually changed
                if old_status != new_status:
                    # Use db_set for submitted documents to avoid validation issues
                    job_doc.db_set("status", new_status, update_modified=False)
                    updated_count += 1
                    
            except Exception as e:
                error_count += 1
                frappe.log_error(
                    f"Error updating status for Transport Job {job_data.name}: {str(e)}",
                    "Transport Job Status Update Error"
                )
                continue
        
        # Commit all changes
        frappe.db.commit()
        
        if updated_count > 0:
            frappe.log_error(
                title="Transport Job Status Update",
                message=f"Updated {updated_count} Transport Job statuses. Errors: {error_count}"
            )
            
    except Exception as e:
        frappe.log_error(
            f"Error in update_transport_job_statuses scheduled task: {str(e)}",
            "Transport Job Status Update Task Error"
        )


def fix_stuck_transport_job_statuses():
    """
    Fix Transport Jobs that are submitted but still showing as Draft.
    This is a safety net for cases where after_submit didn't run properly.
    Runs hourly.
    """
    try:
        # Find submitted jobs that are still Draft
        stuck_jobs = frappe.get_all(
            "Transport Job",
            filters={
                "docstatus": 1,  # Submitted
                "status": ["in", ["Draft", None, ""]]
            },
            fields=["name"],
            limit=100
        )
        
        if not stuck_jobs:
            return
        
        fixed_count = 0
        
        for job_data in stuck_jobs:
            try:
                job_doc = frappe.get_doc("Transport Job", job_data.name)
                
                # Call update_status to determine correct status
                job_doc.update_status()
                new_status = job_doc.status
                
                # If still Draft, force to Submitted
                if not new_status or new_status == "Draft":
                    new_status = "Submitted"
                
                # Update status in database
                job_doc.db_set("status", new_status, update_modified=False)
                fixed_count += 1
                
            except Exception as e:
                frappe.log_error(
                    f"Error fixing status for Transport Job {job_data.name}: {str(e)}",
                    "Transport Job Status Fix Error"
                )
                continue
        
        # Commit all changes
        frappe.db.commit()
        
        if fixed_count > 0:
            frappe.log_error(
                title="Transport Job Status Fix",
                message=f"Fixed {fixed_count} stuck Transport Job statuses"
            )
            
    except Exception as e:
        frappe.log_error(
            f"Error in fix_stuck_transport_job_statuses scheduled task: {str(e)}",
            "Transport Job Status Fix Task Error"
        )


def _update_sla_status_for_doctype(doctype, module, name_field="name", sl_field="logistics_service_level", status_field="sla_status", target_field="sla_target_date", docstatus_filter=None, status_exclude=None):
    """Update sla_status for a doctype. Thresholds come from Logistics Service Level Module child table for the given module."""
    filters = {target_field: ["is", "set"]}
    if docstatus_filter is not None:
        filters["docstatus"] = docstatus_filter
    if status_exclude:
        filters["status"] = ["not in", status_exclude]
    jobs = frappe.get_all(
        doctype,
        filters=filters,
        fields=[name_field, sl_field, target_field, status_field],
        limit=500
    )
    if not jobs:
        return 0
    try:
        from logistics.logistics.doctype.logistics_service_level.logistics_service_level import get_sla_settings_for_module
    except ImportError:
        get_sla_settings_for_module = None
    now = get_datetime(now_datetime())
    updated = 0
    for j in jobs:
        try:
            target = get_datetime(j.get(target_field))
            if not target:
                continue
            sl_name = j.get(sl_field)
            at_risk_hours = 24
            breach_minutes = 0
            if sl_name and get_sla_settings_for_module:
                settings = get_sla_settings_for_module(sl_name, module)
                if settings:
                    at_risk_hours = cint(settings.get("sla_at_risk_hours_before")) or 24
                    breach_minutes = cint(settings.get("sla_breach_grace_minutes")) or 0
            if now > target + timedelta(minutes=breach_minutes):
                new_status = "Breached"
            elif now >= target - timedelta(hours=at_risk_hours):
                new_status = "At Risk"
            else:
                new_status = "On Track"
            if j.get(status_field) != new_status:
                frappe.db.set_value(doctype, j[name_field], status_field, new_status, update_modified=False)
                updated += 1
        except Exception as e:
            frappe.log_error(
                f"Error updating SLA status for {doctype} {j.get(name_field)}: {str(e)}",
                "SLA Status Update Error"
            )
    return updated


def update_sla_statuses():
    """
    Update SLA status (On Track / At Risk / Breached) for Transport Job, Sea Shipment,
    Air Shipment, and Warehouse Job that have sla_target_date set. Uses thresholds from
    Logistics Service Level. Runs hourly.
    """
    try:
        updated = 0
        # Transport Job: module Transport
        updated += _update_sla_status_for_doctype(
            "Transport Job",
            "Transport",
            sl_field="logistics_service_level",
            docstatus_filter=1,
            status_exclude=["Completed", "Cancelled"]
        )
        # Sea Shipment: module Sea Freight
        if frappe.db.table_exists("Sea Shipment") and frappe.db.has_column("Sea Shipment", "sla_target_date"):
            updated += _update_sla_status_for_doctype(
                "Sea Shipment",
                "Sea Freight",
                sl_field="service_level",
                docstatus_filter=1
            )
        # Air Shipment: module Air Freight
        if frappe.db.table_exists("Air Shipment") and frappe.db.has_column("Air Shipment", "sla_target_date"):
            updated += _update_sla_status_for_doctype(
                "Air Shipment",
                "Air Freight",
                sl_field="service_level",
                docstatus_filter=1
            )
        # Warehouse Job: module Warehousing
        if frappe.db.table_exists("Warehouse Job") and frappe.db.has_column("Warehouse Job", "sla_target_date"):
            updated += _update_sla_status_for_doctype(
                "Warehouse Job",
                "Warehousing",
                sl_field="logistics_service_level",
                docstatus_filter=1
            )
        if updated:
            frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            f"Error in update_sla_statuses scheduled task: {str(e)}",
            "SLA Status Task Error"
        )
