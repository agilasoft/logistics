# -*- coding: utf-8 -*-
# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Scheduled Tasks for Transport Module
"""

from __future__ import unicode_literals
import frappe
from frappe import _


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
