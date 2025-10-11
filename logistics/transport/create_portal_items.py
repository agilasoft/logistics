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
    
    # Create Stock Balance portal menu item
    if not frappe.db.exists("Portal Menu Item", "Stock Balance"):
        frappe.get_doc({
            "doctype": "Portal Menu Item",
            "title": "Stock Balance",
            "route": "/warehousing-portal",
            "reference_doctype": "Stock Ledger Entry",
            "icon": "fa fa-warehouse"
        }).insert(ignore_permissions=True)
        print("✅ Stock Balance portal menu item created")
    else:
        print("ℹ️ Stock Balance portal menu item already exists")
    
    frappe.db.commit()
    print("✅ Portal menu items created successfully")


if __name__ == "__main__":
    create_portal_menu_items()
