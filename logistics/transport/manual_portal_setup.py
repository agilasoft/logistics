# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def setup_portal_manually():
    """Manually setup portal menu items through Portal Settings"""
    
    print("🔧 Setting up portal menu items manually...")
    
    # Get Portal Settings
    try:
        portal_settings = frappe.get_single("Portal Settings")
        print("✅ Portal Settings found")
    except:
        print("❌ Portal Settings not found. Please create it first.")
        return
    
    # Check if portal menu items already exist
    existing_items = []
    if hasattr(portal_settings, 'portal_menu_items') and portal_settings.portal_menu_items:
        for item in portal_settings.portal_menu_items:
            existing_items.append(item.title)
    
    print(f"📋 Existing portal menu items: {existing_items}")
    
    # Instructions for manual setup
    print("\n" + "="*60)
    print("📝 MANUAL SETUP INSTRUCTIONS:")
    print("="*60)
    print("1. Go to Portal Settings: /app/portal-settings/Portal%20Settings")
    print("2. In the 'Portal Menu Items' section, add the following items:")
    print()
    print("   Item 1:")
    print("   - Title: Transport Jobs")
    print("   - Route: /transport-portal")
    print("   - Reference DocType: Transport Job")
    print("   - Icon: fa fa-truck")
    print()
    print("   Item 2:")
    print("   - Title: Stock Balance")
    print("   - Route: /warehousing-portal")
    print("   - Reference DocType: Stock Ledger Entry")
    print("   - Icon: fa fa-warehouse")
    print()
    print("3. Save the Portal Settings")
    print("4. The portals will then be available in the customer portal menu")
    print("="*60)
    
    # Verify web pages exist
    print("\n🔍 Verifying web pages...")
    
    if frappe.db.exists("Web Page", "transport-portal"):
        print("✅ Transport portal web page exists")
    else:
        print("❌ Transport portal web page not found")
    
    if frappe.db.exists("Web Page", "warehousing-portal"):
        print("✅ Warehousing portal web page exists")
    else:
        print("❌ Warehousing portal web page not found")
    
    print("\n✅ Manual setup instructions provided!")


if __name__ == "__main__":
    setup_portal_manually()
