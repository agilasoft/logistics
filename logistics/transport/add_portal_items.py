# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def add_portal_menu_items():
    """Add portal menu items to Portal Settings"""
    
    # Get or create Portal Settings
    try:
        portal_settings = frappe.get_single("Portal Settings")
    except:
        # Create portal settings if it doesn't exist
        portal_settings = frappe.get_doc({
            "doctype": "Portal Settings",
            "default_portal_home": "/transport-portal"
        })
        portal_settings.insert(ignore_permissions=True)
        print("✅ Portal Settings created")
    
    # Add Transport Jobs menu item
    transport_exists = False
    portal_menu_items = portal_settings.get("portal_menu_items") or []
    for item in portal_menu_items:
        if item.get("title") == "Transport Jobs":
            transport_exists = True
            break
    
    if not transport_exists:
        portal_settings.append("portal_menu_items", {
            "title": "Transport Jobs",
            "route": "/transport-portal",
            "reference_doctype": "Transport Job",
            "icon": "fa fa-truck"
        })
        print("✅ Transport Jobs menu item added")
    else:
        print("ℹ️ Transport Jobs menu item already exists")
    
    # Stock Balance menu item is already defined in hooks.py
    # No need to add it here to avoid duplicates
    print("ℹ️ Stock Balance menu item is managed by hooks.py")
    
    # Save the portal settings
    portal_settings.save(ignore_permissions=True)
    frappe.db.commit()
    print("✅ Portal menu items added to Portal Settings")


if __name__ == "__main__":
    add_portal_menu_items()
