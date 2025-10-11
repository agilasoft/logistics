# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def add_portal_items_to_settings():
    """Add portal menu items directly to Portal Settings"""
    
    print("🔧 Adding portal menu items to Portal Settings...")
    
    try:
        # Get Portal Settings
        portal_settings = frappe.get_single("Portal Settings")
        print("✅ Portal Settings found")
        
        # Clear existing portal menu items
        if hasattr(portal_settings, 'menu'):
            portal_settings.menu = []
            print("🧹 Cleared existing portal menu items")
        
        # Add Transport Jobs
        portal_settings.append("menu", {
            "title": "Transport Jobs",
            "route": "/transport-jobs",
            "reference_doctype": "Transport Job",
            "icon": "fa fa-truck"
        })
        print("✅ Transport Jobs menu item added")
        
        # Add Stock Balance
        portal_settings.append("menu", {
            "title": "Stock Balance", 
            "route": "/stock-balance",
            "reference_doctype": "Item",
            "icon": "fa fa-warehouse"
        })
        print("✅ Stock Balance menu item added")
        
        # Save the settings
        portal_settings.save(ignore_permissions=True)
        frappe.db.commit()
        
        print("✅ Portal menu items saved to Portal Settings!")
        
        # Verify the items were added
        portal_settings.reload()
        if hasattr(portal_settings, 'menu') and portal_settings.menu:
            print(f"📋 Found {len(portal_settings.menu)} portal menu items:")
            for item in portal_settings.menu:
                print(f"   - {item.title}: {item.route}")
        else:
            print("❌ No portal menu items found after saving")
            
    except Exception as e:
        print(f"❌ Error adding portal menu items: {e}")
        frappe.log_error(f"Error adding portal menu items: {e}")


if __name__ == "__main__":
    add_portal_items_to_settings()
