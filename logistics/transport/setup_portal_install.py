# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def setup_portal_menu_items():
    """Setup portal menu items for existing installations"""
    
    print("🔧 Setting up portal menu items for Logistics app...")
    
    # Get or create Portal Settings
    try:
        portal_settings = frappe.get_single("Portal Settings")
        print("✅ Portal Settings found")
    except Exception:
        # Create portal settings if it doesn't exist
        portal_settings = frappe.get_doc({
            "doctype": "Portal Settings",
            "default_portal_home": "/transport-portal"
        })
        portal_settings.insert(ignore_permissions=True)
        print("✅ Portal Settings created")
    
    # Check if items already exist
    existing_titles = []
    if hasattr(portal_settings, 'portal_menu_items') and portal_settings.portal_menu_items:
        for item in portal_settings.portal_menu_items:
            existing_titles.append(item.title)
    
    # Add Transport Jobs portal menu item if not exists
    if "Transport Jobs" not in existing_titles:
        portal_settings.append("portal_menu_items", {
            "title": "Transport Jobs",
            "route": "/transport-portal",
            "reference_doctype": "Transport Job",
            "icon": "fa fa-truck"
        })
        print("✅ Transport Jobs portal menu item added")
    else:
        print("ℹ️ Transport Jobs portal menu item already exists")
    
    # Stock Balance is already defined in hooks.py
    # No need to add it here to avoid duplicates
    print("ℹ️ Stock Balance menu item is managed by hooks.py")
    
    # Save the portal settings
    portal_settings.save(ignore_permissions=True)
    frappe.db.commit()
    
    print("✅ Portal menu items setup complete!")
    print("📋 Available portal menu items:")
    for item in portal_settings.portal_menu_items:
        print(f"   - {item.title} ({item.route})")
    
    return True


if __name__ == "__main__":
    setup_portal_menu_items()
