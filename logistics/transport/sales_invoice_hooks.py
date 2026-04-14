# -*- coding: utf-8 -*-
# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Sales Invoice hooks for Transport Job validation
"""
import frappe
from frappe import _


def validate_transport_job_status(doc, method=None):
    """
    Validate that if Sales Invoice is linked to a Transport Job via job_number,
    the Transport Job status must be "Completed".
    
    This prevents creating Sales Invoices for Transport Jobs that are not yet completed.
    """
    if not doc.job_number:
        # No job_number, so no Transport Job to validate
        return
    
    try:
        # Get Job Number to find the linked Transport Job
        jcn = frappe.get_doc("Job Number", doc.job_number)
        
        # Check if this Job Number is linked to a Transport Job
        if jcn.job_type != "Transport Job" or not jcn.job_no:
            # Not linked to a Transport Job, skip validation
            return
        
        # Get the Transport Job
        transport_job_name = jcn.job_no
        if not frappe.db.exists("Transport Job", transport_job_name):
            # Transport Job doesn't exist, skip validation
            return
        
        # Get Transport Job status
        transport_job_status = frappe.db.get_value("Transport Job", transport_job_name, "status")
        
        # Validate status is "Completed"
        if transport_job_status != "Completed":
            frappe.throw(
                _("Cannot create Sales Invoice. Transport Job {0} status must be 'Completed'. Current status: {1}").format(
                    transport_job_name,
                    transport_job_status or "Draft"
                )
            )
    
    except frappe.DoesNotExistError:
        # Job Number doesn't exist, skip validation
        pass
    except Exception as e:
        # Log error but don't block if there's an unexpected issue
        frappe.log_error(
            f"Error validating Transport Job status for Sales Invoice {doc.name}: {str(e)}",
            "Sales Invoice Transport Job Validation Error"
        )
