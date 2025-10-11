# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def setup_portal_final():
    """Final setup for portal menu items"""
    
    print("🎯 FINAL PORTAL SETUP")
    print("=" * 50)
    
    # Check web pages
    print("🔍 Checking web pages...")
    web_pages = frappe.get_all("Web Page", fields=["name", "title", "route"])
    for page in web_pages:
        if "transport" in page.route or "warehousing" in page.route:
            print(f"✅ {page.title}: {page.route}")
    
    # Check Portal Settings
    print("\n🔍 Checking Portal Settings...")
    try:
        portal_settings = frappe.get_single("Portal Settings")
        print("✅ Portal Settings exists")
        
        # Check if portal menu items field exists
        if hasattr(portal_settings, 'portal_menu_items'):
            print("✅ Portal menu items field exists")
            if portal_settings.portal_menu_items:
                print(f"📋 Found {len(portal_settings.portal_menu_items)} portal menu items")
                for item in portal_settings.portal_menu_items:
                    print(f"   - {item.title}: {item.route}")
            else:
                print("📋 No portal menu items found")
        else:
            print("❌ Portal menu items field does not exist")
    except Exception as e:
        print(f"❌ Error checking Portal Settings: {e}")
    
    print("\n" + "=" * 50)
    print("📝 MANUAL SETUP REQUIRED:")
    print("=" * 50)
    print("The portal menu items are defined in hooks.py but need to be")
    print("manually added to Portal Settings. Here's what to do:")
    print("")
    print("1. Go to: /app/portal-settings/Portal%20Settings")
    print("2. Look for 'Portal Menu Items' section")
    print("3. Add these items manually:")
    print("")
    print("   Item 1:")
    print("   - Title: Transport Jobs")
    print("   - Route: /transport-portal")
    print("   - Reference DocType: Transport Job")
    print("   - Icon: fa fa-truck")
    print("")
    print("   Item 2:")
    print("   - Title: Stock Balance")
    print("   - Route: /warehousing-portal")
    print("   - Reference DocType: Stock Ledger Entry")
    print("   - Icon: fa fa-warehouse")
    print("")
    print("4. Save the Portal Settings")
    print("5. The portals will then appear in the customer portal menu")
    print("")
    print("🌐 Portal URLs:")
    print("- Transport Jobs: https://logistics.agilasoft.com/transport-portal")
    print("- Stock Balance: https://logistics.agilasoft.com/warehousing-portal")
    print("=" * 50)


if __name__ == "__main__":
    setup_portal_final()
