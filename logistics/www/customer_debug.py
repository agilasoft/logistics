# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def get_context(context):
    """Debug customer detection"""
    user = frappe.session.user
    user_roles = frappe.get_roles()
    
    # Try different methods to find customer
    debug_info = {
        "user": user,
        "roles": user_roles,
        "form_dict": frappe.form_dict,
        "session_customer": frappe.session.get('customer')
    }
    
    # Method 1: Direct email match
    direct_customers = frappe.get_all(
        "Customer",
        filters={"email_id": user},
        fields=["name", "customer_name", "email_id"]
    )
    debug_info["direct_customers"] = direct_customers
    
    # Method 2: Through Contact
    contact = frappe.get_value("Contact", {"email_id": user}, "name")
    debug_info["contact"] = contact
    
    if contact:
        customer_links = frappe.get_all(
            "Dynamic Link",
            filters={
                "parent": contact,
                "link_doctype": "Customer"
            },
            fields=["link_name"]
        )
        debug_info["customer_links"] = customer_links
    
    # Method 3: Check Portal Users
    portal_users = frappe.get_all(
        "Portal User",
        filters={"user": user},
        fields=["parent", "user"]
    )
    debug_info["portal_users"] = portal_users
    
    # Method 4: All customers with this email
    all_customers = frappe.get_all(
        "Customer",
        filters={"email_id": ["like", f"%{user}%"]},
        fields=["name", "customer_name", "email_id"]
    )
    debug_info["all_customers"] = all_customers
    
    context.update({
        "title": "Customer Debug Information",
        "debug_info": debug_info
    })
    
    return context
