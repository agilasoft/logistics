# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def add_portal_user_permissions(customer_doc, method):
    """
    Hook to add user permissions when portal users are added to a customer
    This function is called when Customer doctype is saved
    """
    try:
        # Check if portal_users field exists and has data
        if hasattr(customer_doc, 'portal_users') and customer_doc.portal_users:
            for portal_user_row in customer_doc.portal_users:
                if portal_user_row.user:
                    # Add permissions for Customer doctype
                    add_customer_permissions(customer_doc.name, portal_user_row.user)
                    
                    # Add permissions for User doctype (for the portal user themselves)
                    add_user_permissions(portal_user_row.user)
                    
                    frappe.msgprint(f"Added permissions for portal user: {portal_user_row.user}")
        
    except Exception as e:
        frappe.log_error(f"Error adding portal user permissions: {str(e)}", "Portal User Permissions")


def add_customer_permissions(customer_name, user_email):
    """
    Add user permissions for Customer doctype
    """
    try:
        # Check if permission already exists
        existing_permission = frappe.get_value(
            "User Permission",
            {
                "user": user_email,
                "allow": "Customer",
                "for_value": customer_name
            },
            "name"
        )
        
        if not existing_permission:
            # Create new user permission for Customer
            permission_doc = frappe.get_doc({
                "doctype": "User Permission",
                "user": user_email,
                "allow": "Customer",
                "for_value": customer_name,
                "apply_to_all_doctypes": 0,
                "applicable_for": "Customer"
            })
            permission_doc.insert(ignore_permissions=True)
            frappe.db.commit()
            
            frappe.log_error(f"Created Customer permission for user {user_email} on customer {customer_name}", "Portal User Permissions")
        
    except Exception as e:
        frappe.log_error(f"Error adding Customer permissions for {user_email}: {str(e)}", "Portal User Permissions")


def add_user_permissions(user_email):
    """
    Add user permissions for User doctype (self-permission)
    """
    try:
        # Check if permission already exists
        existing_permission = frappe.get_value(
            "User Permission",
            {
                "user": user_email,
                "allow": "User",
                "for_value": user_email
            },
            "name"
        )
        
        if not existing_permission:
            # Create new user permission for User (self-permission)
            permission_doc = frappe.get_doc({
                "doctype": "User Permission",
                "user": user_email,
                "allow": "User",
                "for_value": user_email,
                "apply_to_all_doctypes": 0,
                "applicable_for": "User"
            })
            permission_doc.insert(ignore_permissions=True)
            frappe.db.commit()
            
            frappe.log_error(f"Created User permission for user {user_email}", "Portal User Permissions")
        
    except Exception as e:
        frappe.log_error(f"Error adding User permissions for {user_email}: {str(e)}", "Portal User Permissions")


def remove_portal_user_permissions(customer_doc, method):
    """
    Hook to remove user permissions when portal users are removed from a customer
    This function is called when Customer doctype is saved
    """
    try:
        # Get the original document to compare changes
        if customer_doc.get("__islocal") or not customer_doc.name:
            return
            
        # Get the original portal users
        original_doc = frappe.get_doc("Customer", customer_doc.name)
        original_portal_users = []
        
        if hasattr(original_doc, 'portal_users') and original_doc.portal_users:
            original_portal_users = [row.user for row in original_doc.portal_users if row.user]
        
        # Get current portal users
        current_portal_users = []
        if hasattr(customer_doc, 'portal_users') and customer_doc.portal_users:
            current_portal_users = [row.user for row in customer_doc.portal_users if row.user]
        
        # Find removed users
        removed_users = set(original_portal_users) - set(current_portal_users)
        
        # Remove permissions for removed users
        for user_email in removed_users:
            remove_customer_permissions(customer_doc.name, user_email)
            frappe.msgprint(f"Removed permissions for portal user: {user_email}")
        
    except Exception as e:
        frappe.log_error(f"Error removing portal user permissions: {str(e)}", "Portal User Permissions")


def remove_customer_permissions(customer_name, user_email):
    """
    Remove user permissions for Customer doctype
    """
    try:
        # Find and delete the permission
        permissions = frappe.get_all(
            "User Permission",
            filters={
                "user": user_email,
                "allow": "Customer",
                "for_value": customer_name
            },
            fields=["name"]
        )
        
        for permission in permissions:
            frappe.delete_doc("User Permission", permission.name, ignore_permissions=True)
            frappe.db.commit()
            
        frappe.log_error(f"Removed Customer permission for user {user_email} on customer {customer_name}", "Portal User Permissions")
        
    except Exception as e:
        frappe.log_error(f"Error removing Customer permissions for {user_email}: {str(e)}", "Portal User Permissions")
