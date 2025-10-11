# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def get_context(context):
    """Debug transport jobs data"""
    user = frappe.session.user
    
    # Get customer from the same logic as portal
    customer = get_customer_from_request()
    
    debug_info = {
        "user": user,
        "customer": customer,
        "total_transport_jobs": 0,
        "customer_jobs": [],
        "all_jobs_sample": [],
        "customer_info": {}
    }
    
    # Get total transport jobs
    try:
        total_jobs = frappe.db.count("Transport Job")
        debug_info["total_transport_jobs"] = total_jobs
    except Exception as e:
        debug_info["error_total_jobs"] = str(e)
    
    # Try to get Transport Job fields
    try:
        # Get one job to see what fields exist
        sample_job = frappe.get_all("Transport Job", limit=1)
        if sample_job:
            debug_info["sample_job_fields"] = list(sample_job[0].keys())
        else:
            debug_info["sample_job_fields"] = "No jobs found"
    except Exception as e:
        debug_info["error_sample_job"] = str(e)
    
    # Get customer info
    if customer:
        try:
            customer_doc = frappe.get_doc("Customer", customer)
            debug_info["customer_info"] = {
                "name": customer_doc.name,
                "customer_name": customer_doc.customer_name,
                "email_id": customer_doc.email_id
            }
        except Exception as e:
            debug_info["error_customer_info"] = str(e)
        
        # Get jobs for this customer - try without status field first
        try:
            customer_jobs = frappe.get_all(
                "Transport Job",
                filters={"customer": customer},
                fields=["name", "customer", "booking_date"],
                limit=10
            )
            debug_info["customer_jobs"] = customer_jobs
        except Exception as e:
            debug_info["error_customer_jobs"] = str(e)
    
    # Get sample of all jobs - try without status field first
    try:
        all_jobs = frappe.get_all(
            "Transport Job",
            fields=["name", "customer", "booking_date"],
            limit=10
        )
        debug_info["all_jobs_sample"] = all_jobs
    except Exception as e:
        debug_info["error_all_jobs"] = str(e)
    
    context.update({
        "title": "Transport Jobs Debug",
        "debug_info": debug_info
    })
    
    return context


def get_customer_from_request():
    """Extract customer from request parameters - same logic as portal"""
    # Try URL parameter first
    customer = frappe.form_dict.get('customer')
    if customer:
        return customer
    
    # Try session variable
    customer = frappe.session.get('customer')
    if customer:
        return customer
    
    # Try user email - improved logic
    user = frappe.session.user
    if user and user != "Guest":
        # Method 1: Check Portal Users field in Customer doctype
        try:
            portal_users = frappe.get_all(
                "Portal User",
                filters={"user": user},
                fields=["parent"],
                limit=1
            )
            if portal_users:
                return portal_users[0].parent
        except Exception as e:
            pass
        
        # Method 2: Direct email match in Customer
        customers = frappe.get_all(
            "Customer",
            filters={"email_id": user},
            fields=["name"],
            limit=1
        )
        if customers:
            return customers[0].name
        
        # Method 3: Through Contact links
        contact = frappe.get_value("Contact", {"email_id": user}, "name")
        if contact:
            customer_links = frappe.get_all(
                "Dynamic Link",
                filters={
                    "parent": contact,
                    "link_doctype": "Customer"
                },
                fields=["link_name"],
                limit=1
            )
            if customer_links:
                return customer_links[0].link_name
    
    return None
