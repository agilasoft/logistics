# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def get_context(context):
    """Get context for warehouse jobs web page"""
    
    # Get all customers for user
    all_customers = get_customers_for_user()
    
    if not all_customers:
        # For testing, use a default customer or show a message
        context.update({
            "title": "Warehouse Jobs",
            "page_title": "Warehouse Jobs",
            "error_message": "Customer not found. Please contact support."
        })
        return context
    
    # Get selected customer from request or use first one
    customer = get_customer_from_request()
    
    # If user has multiple customers, show customer selection
    if len(all_customers) > 1:
        context.update({
            "all_customers": all_customers,
            "selected_customer": customer,
            "show_customer_dropdown": True,
            "title": "Warehouse Jobs - Select Customer",
            "page_title": "Warehouse Jobs"
        })
        
        # If no customer selected, show selection page
        if not customer:
            return context
    
    # Get customer info
    try:
        customer_doc = frappe.get_doc("Customer", customer)
        customer_name = customer_doc.customer_name
        customer_email = customer_doc.email_id
    except:
        customer_name = "Unknown Customer"
        customer_email = ""
    
    # Get warehouse jobs for customer
    jobs = get_customer_warehouse_jobs(customer)
    
    # Get filter parameters
    form_dict = frappe.form_dict or {}
    job_type = form_dict.get('job_type')
    status = form_dict.get('status')
    date_from = form_dict.get('date_from')
    date_to = form_dict.get('date_to')
    
    # Filter jobs based on parameters
    filtered_jobs = jobs
    if job_type:
        filtered_jobs = [job for job in filtered_jobs if job.get('type') == job_type]
    if status:
        filtered_jobs = [job for job in filtered_jobs if job.get('status') == status]
    
    # Get available job types for filter
    available_types = list(set([job.get('type') for job in jobs if job.get('type')]))
    available_statuses = list(set([job.get('status') for job in jobs if job.get('status')]))
    
    # Calculate summary statistics
    total_jobs = len(filtered_jobs)
    open_jobs = len([job for job in filtered_jobs if job.get('status') == 'Open'])
    in_progress_jobs = len([job for job in filtered_jobs if job.get('status') == 'In Progress'])
    completed_jobs = len([job for job in filtered_jobs if job.get('status') == 'Completed'])
    
    context.update({
        "customer_id": customer,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "jobs": filtered_jobs,
        "total_jobs": total_jobs,
        "open_jobs": open_jobs,
        "in_progress_jobs": in_progress_jobs,
        "completed_jobs": completed_jobs,
        "available_types": available_types,
        "available_statuses": available_statuses,
        "job_type": job_type,
        "status": status,
        "date_from": date_from,
        "date_to": date_to,
        "title": f"Warehouse Jobs - {customer_name}",
        "page_title": "Warehouse Jobs"
    })
    
    return context


def get_customer_from_request():
    """Get customer from request parameters or session"""
    
    # Try to get customer from URL parameters
    customer = frappe.form_dict.get('customer')
    if customer:
        return customer
    
    # Try to get customer from session
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
            frappe.log_error(f"Error checking portal users: {str(e)}", "Warehouse Jobs Portal")
        
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
            # Get customer links from contact
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
        
        # Method 4: Check if user has Customer role and find through contact
        try:
            user_doc = frappe.get_doc("User", user)
            if user_doc.email:
                # Find customer by email
                customers = frappe.get_all("Customer", 
                    filters={"email_id": user_doc.email}, 
                    fields=["name"]
                )
                if customers:
                    return customers[0].name
        except Exception as e:
            frappe.log_error(f"Error getting customer from user email: {str(e)}", "Warehouse Jobs Portal")
    
    return None


def get_customers_for_user():
    """Get all customers associated with the current user"""
    user = frappe.session.user
    customers = []
    
    if user and user != "Guest":
        # Method 1: Check Portal Users field in Customer doctype
        try:
            portal_users = frappe.get_all(
                "Portal User",
                filters={"user": user, "parenttype": "Customer"},
                fields=["parent", "parenttype"]
            )
            for pu in portal_users:
                customers.append(pu.parent)
        except Exception as e:
            pass
        
        # Method 2: Direct email match in Customer
        direct_customers = frappe.get_all(
            "Customer",
            filters={"email_id": user},
            fields=["name"]
        )
        for dc in direct_customers:
            if dc.name not in customers:
                customers.append(dc.name)
        
        # Method 3: Through Contact links
        contact = frappe.get_value("Contact", {"email_id": user}, "name")
        if contact:
            customer_links = frappe.get_all(
                "Dynamic Link",
                filters={
                    "parent": contact,
                    "link_doctype": "Customer"
                },
                fields=["link_name"]
            )
            for cl in customer_links:
                if cl.link_name not in customers:
                    customers.append(cl.link_name)
    
    return customers


def get_customer_warehouse_jobs(customer):
    """Get warehouse jobs for customer"""
    
    try:
        # Get warehouse jobs for the customer
        jobs = frappe.get_all("Warehouse Job",
            filters={"customer": customer},
            fields=["name", "type", "job_open_date", "status", "reference_order_type", "reference_order"],
            order_by="job_open_date desc"
        )
        
        # Get additional details for each job
        for job in jobs:
            # Get operations count
            operations_count = frappe.db.count("Warehouse Job Operations", {"parent": job.name})
            job["operations_count"] = operations_count
            
            # Get items count
            items_count = frappe.db.count("Warehouse Job Item", {"parent": job.name})
            job["items_count"] = items_count
            
            # Get charges total
            charges_total = frappe.db.sql("""
                SELECT SUM(amount) as total
                FROM `tabWarehouse Job Charges`
                WHERE parent = %s
            """, (job.name,), as_dict=True)
            job["charges_total"] = charges_total[0].total if charges_total and charges_total[0].total else 0
        
        return jobs
    except Exception as e:
        frappe.log_error(f"Error getting customer warehouse jobs: {e}")
        return []
