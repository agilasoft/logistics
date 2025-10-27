# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def create_portal_menu_items():
    """Create portal menu items directly in the database"""
    
    # Create Transport Jobs portal menu item
    if not frappe.db.exists("Portal Menu Item", "Transport Jobs"):
        frappe.get_doc({
            "doctype": "Portal Menu Item",
            "title": "Transport Jobs",
            "route": "/transport-portal",
            "reference_doctype": "Transport Job",
            "icon": "fa fa-truck"
        }).insert(ignore_permissions=True)
        print("✅ Transport Jobs portal menu item created")
    else:
        print("ℹ️ Transport Jobs portal menu item already exists")
    
    # Stock Balance is already defined in hooks.py
    # No need to add it here to avoid duplicates
    print("ℹ️ Stock Balance menu item is managed by hooks.py")
    
    frappe.db.commit()
    print("✅ Portal menu items created successfully")


if __name__ == "__main__":
    create_portal_menu_items()
