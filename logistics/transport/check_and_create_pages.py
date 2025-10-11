# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def check_and_create_pages():
    """Check existing web pages and create missing ones"""
    
    print("🔍 Checking existing web pages...")
    
    # Check what web pages exist
    web_pages = frappe.get_all("Web Page", fields=["name", "title", "route"])
    print(f"📋 Found {len(web_pages)} web pages:")
    for page in web_pages:
        print(f"   - {page.name}: {page.title} ({page.route})")
    
    # Check for transport portal
    if not frappe.db.exists("Web Page", "transport-portal"):
        print("❌ Transport portal web page not found, creating...")
        create_transport_portal()
    else:
        print("✅ Transport portal web page exists")
    
    # Check for warehousing portal
    if not frappe.db.exists("Web Page", "warehousing-portal"):
        print("❌ Warehousing portal web page not found, creating...")
        create_warehousing_portal()
    else:
        print("✅ Warehousing portal web page exists")
    
    print("\n🎯 Portal menu items need to be added manually in Portal Settings:")
    print("1. Go to: /app/portal-settings/Portal%20Settings")
    print("2. Add these items in 'Portal Menu Items' section:")
    print("   - Title: Transport Jobs, Route: /transport-portal, Icon: fa fa-truck")
    print("   - Title: Stock Balance, Route: /warehousing-portal, Icon: fa fa-warehouse")


def create_transport_portal():
    """Create transport portal web page"""
    try:
        transport_page = frappe.get_doc({
            "doctype": "Web Page",
            "title": "Transport Jobs Portal",
            "route": "/transport-portal",
            "published": 1,
            "content_type": "HTML",
            "main_section": '<div id="transport-portal-content">Loading transport portal...</div>',
            "meta_title": "Transport Jobs Portal",
            "meta_description": "Track your transport jobs and shipments"
        })
        transport_page.insert(ignore_permissions=True)
        print("✅ Transport portal web page created")
    except Exception as e:
        print(f"❌ Error creating transport portal: {e}")


def create_warehousing_portal():
    """Create warehousing portal web page"""
    try:
        warehousing_page = frappe.get_doc({
            "doctype": "Web Page",
            "title": "Stock Balance Portal",
            "route": "/warehousing-portal",
            "published": 1,
            "content_type": "HTML",
            "main_section": '<div id="warehousing-portal-content">Loading stock balance portal...</div>',
            "meta_title": "Stock Balance Portal",
            "meta_description": "View your stock balance and inventory"
        })
        warehousing_page.insert(ignore_permissions=True)
        print("✅ Warehousing portal web page created")
    except Exception as e:
        print(f"❌ Error creating warehousing portal: {e}")


if __name__ == "__main__":
    check_and_create_pages()
