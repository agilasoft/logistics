# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def check_portal_structure():
    """Check Portal Settings structure and create portal menu items"""
    
    print("🔍 Checking Portal Settings structure...")
    
    try:
        # Get Portal Settings
        portal_settings = frappe.get_single("Portal Settings")
        print("✅ Portal Settings found")
        
        # Check all fields in Portal Settings
        print("\n📋 Portal Settings fields:")
        for field in portal_settings.meta.fields:
            print(f"   - {field.fieldname}: {field.fieldtype}")
        
        # Check if there's a portal_menu_items field
        if hasattr(portal_settings, 'portal_menu_items'):
            print("\n✅ portal_menu_items field exists")
            if portal_settings.portal_menu_items:
                print(f"📋 Found {len(portal_settings.portal_menu_items)} items:")
                for item in portal_settings.portal_menu_items:
                    print(f"   - {item.title}: {item.route}")
            else:
                print("📋 No portal menu items found")
        else:
            print("\n❌ portal_menu_items field does not exist")
        
        # Try to create portal menu items directly
        print("\n🔧 Creating portal menu items directly...")
        
        # Create Transport Jobs portal menu item
        try:
            transport_item = frappe.get_doc({
                "doctype": "Portal Menu Item",
                "title": "Transport Jobs",
                "route": "/transport-jobs",
                "reference_doctype": "Transport Job",
                "icon": "fa fa-truck"
            })
            transport_item.insert(ignore_permissions=True)
            print("✅ Transport Jobs portal menu item created")
        except Exception as e:
            print(f"❌ Error creating Transport Jobs: {e}")
        
        # Create Stock Balance portal menu item
        try:
            stock_item = frappe.get_doc({
                "doctype": "Portal Menu Item",
                "title": "Stock Balance",
                "route": "/stock-balance", 
                "reference_doctype": "Stock Ledger Entry",
                "icon": "fa fa-warehouse"
            })
            stock_item.insert(ignore_permissions=True)
            print("✅ Stock Balance portal menu item created")
        except Exception as e:
            print(f"❌ Error creating Stock Balance: {e}")
        
        frappe.db.commit()
        print("\n✅ Portal menu items creation complete!")
        
    except Exception as e:
        print(f"❌ Error checking portal structure: {e}")
        frappe.log_error(f"Error checking portal structure: {e}")


if __name__ == "__main__":
    check_portal_structure()
