# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def get_context(context):
    """Debug customer lookup for portal pages"""
    
    user = frappe.session.user
    debug_info = {
        "user": user,
        "session_customer": frappe.session.get('customer'),
        "form_dict_customer": frappe.form_dict.get('customer'),
        "all_customers": [],
        "customer_lookup_methods": {}
    }
    
    # Test all customer lookup methods
    try:
        # Method 1: Portal Users
        portal_users = frappe.get_all(
            "Portal User",
            filters={"user": user},
            fields=["parent", "parenttype"]
        )
        debug_info["customer_lookup_methods"]["portal_users"] = portal_users
        
        # Method 2: Direct email match
        direct_customers = frappe.get_all(
            "Customer",
            filters={"email_id": user},
            fields=["name"]
        )
        debug_info["customer_lookup_methods"]["direct_customers"] = direct_customers
        
        # Method 3: Contact links
        contact = frappe.get_value("Contact", {"email_id": user}, "name")
        debug_info["customer_lookup_methods"]["contact"] = contact
        
        if contact:
            customer_links = frappe.get_all(
                "Dynamic Link",
                filters={
                    "parent": contact,
                    "link_doctype": "Customer"
                },
                fields=["link_name"]
            )
            debug_info["customer_lookup_methods"]["customer_links"] = customer_links
        
        # Method 4: User email
        try:
            user_doc = frappe.get_doc("User", user)
            debug_info["customer_lookup_methods"]["user_email"] = user_doc.email
        except Exception as e:
            debug_info["customer_lookup_methods"]["user_email_error"] = str(e)
        
        # Get all customers using the same logic as warehousing_portal
        all_customers = get_customers_for_user()
        debug_info["all_customers"] = all_customers
        
    except Exception as e:
        debug_info["error"] = str(e)
    
    context.update({
        "debug_info": debug_info,
        "title": "Customer Debug - Portal",
        "page_title": "Customer Debug"
    })
    
    return context


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
