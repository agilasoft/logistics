# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def add_portal_menu_items():
    """Add portal menu items to Portal Settings"""
    
    print("🔧 Adding portal menu items to Portal Settings...")
    
    # Get Portal Settings
    try:
        portal_settings = frappe.get_single("Portal Settings")
        print("✅ Portal Settings found")
    except:
        print("❌ Portal Settings not found")
        return
    
    # Check existing items
    existing_items = []
    if hasattr(portal_settings, 'portal_menu_items') and portal_settings.portal_menu_items:
        for item in portal_settings.portal_menu_items:
            existing_items.append(item.title)
        print(f"📋 Existing portal menu items: {existing_items}")
    else:
        print("📋 No existing portal menu items found")
    
    # Add Transport Jobs if not exists
    if "Transport Jobs" not in existing_items:
        try:
            # Create new portal menu item
            new_item = frappe.get_doc({
                "doctype": "Portal Menu Item",
                "title": "Transport Jobs",
                "route": "/transport-portal",
                "reference_doctype": "Transport Job",
                "icon": "fa fa-truck"
            })
            new_item.insert(ignore_permissions=True)
            print("✅ Transport Jobs portal menu item created")
        except Exception as e:
            print(f"❌ Error creating Transport Jobs menu item: {e}")
    else:
        print("ℹ️ Transport Jobs menu item already exists")
    
    # Add Stock Balance if not exists
    if "Stock Balance" not in existing_items:
        try:
            # Create new portal menu item
            new_item = frappe.get_doc({
                "doctype": "Portal Menu Item",
                "title": "Stock Balance",
                "route": "/warehousing-portal",
                "reference_doctype": "Stock Ledger Entry",
                "icon": "fa fa-warehouse"
            })
            new_item.insert(ignore_permissions=True)
            print("✅ Stock Balance portal menu item created")
        except Exception as e:
            print(f"❌ Error creating Stock Balance menu item: {e}")
    else:
        print("ℹ️ Stock Balance menu item already exists")
    
    frappe.db.commit()
    print("✅ Portal menu items setup complete!")
    
    # Verify the items were added
    print("\n🔍 Verifying portal menu items...")
    try:
        portal_settings = frappe.get_single("Portal Settings")
        if hasattr(portal_settings, 'portal_menu_items') and portal_settings.portal_menu_items:
            print("📋 Portal menu items in Portal Settings:")
            for item in portal_settings.portal_menu_items:
                print(f"   - {item.title}: {item.route}")
        else:
            print("❌ No portal menu items found in Portal Settings")
    except Exception as e:
        print(f"❌ Error verifying portal menu items: {e}")


if __name__ == "__main__":
    add_portal_menu_items()
