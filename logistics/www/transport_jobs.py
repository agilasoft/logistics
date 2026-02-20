# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def get_context(context):
    """Get context for transport jobs web page"""
    
    # Get all customers for user
    all_customers = get_customers_for_user()
    
    if not all_customers:
        # For testing, use a default customer or show a message
        context.update({
            "title": "Transport Jobs",
            "page_title": "Transport Jobs",
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
            "title": "Transport Jobs - Select Customer",
            "page_title": "Transport Jobs"
        })
        
        # If no customer selected, show selection page
        if not customer:
            return context
    
    # Get customer info
    try:
        customer_doc = frappe.get_doc("Customer", customer)
        customer_name = customer_doc.customer_name
        customer_email = customer_doc.email_id
    except Exception:
        customer_name = "Unknown Customer"
        customer_email = ""
    
    # Get transport jobs for customer
    jobs = get_customer_jobs(customer)
    
    # Check if any job has legs with "Started" status to show vehicle tracking
    show_vehicle_tracking = False
    for job in jobs:
        if job.get('legs'):
            for leg in job['legs']:
                if leg.get('status') == 'Started':
                    show_vehicle_tracking = True
                    break
        if show_vehicle_tracking:
            break
    
    # Get transport settings for map configuration
    try:
        transport_settings = frappe.get_single("Transport Settings")
        map_renderer = getattr(transport_settings, 'map_renderer', 'OpenStreetMap')
    except Exception:
        map_renderer = 'OpenStreetMap'
    
    context.update({
        "customer_id": customer,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "jobs": jobs,
        "total_jobs": len(jobs),
        "title": f"Transport Jobs - {customer_name}",
        "page_title": "Transport Jobs",
        "map_renderer": map_renderer,
        "show_vehicle_tracking": show_vehicle_tracking,
        "show_route_map": show_vehicle_tracking
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
            frappe.log_error(f"Error checking portal users: {str(e)}", "Transport Jobs Portal")
        
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
            frappe.log_error(f"Error getting customer from user email: {str(e)}", "Transport Jobs Portal")
    
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


def get_customer_jobs(customer):
    """Get transport jobs for customer"""
    
    try:
        # Get transport jobs for the customer
        jobs = frappe.get_all("Transport Job",
            filters={"customer": customer},
            fields=["name", "booking_date", "vehicle_type", "status"],
            order_by="booking_date desc"
        )
        
        # Get legs for each job
        for job in jobs:
            legs = frappe.get_all("Transport Leg",
                filters={"transport_job": job.name},
                fields=["name", "status", "pick_address", "drop_address", "run_sheet", "route_map"]
            )
            job["legs"] = legs
        
        return jobs
    except Exception as e:
        frappe.log_error(f"Error getting customer jobs: {e}")
        return []
