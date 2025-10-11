# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def after_install():
    """Setup portal menu items after app installation"""
    
    print("🚀 Setting up Logistics app portal menu items...")
    
    # Create web pages for the portals
    create_portal_web_pages()
    
    # The portal menu items are defined in hooks.py and will be automatically
    # available in Portal Settings. No need to manually add them here.
    
    print("✅ Portal setup complete!")
    print("📋 Portal menu items configured in hooks.py:")
    print("   - Transport Jobs (/transport-portal)")
    print("   - Stock Balance (/warehousing-portal)")
    print("🎉 Logistics app installation complete!")
    print("")
    print("📝 Next steps:")
    print("1. Go to Portal Settings: /app/portal-settings/Portal%20Settings")
    print("2. The portal menu items should be automatically available")
    print("3. Configure access permissions as needed")


def create_portal_web_pages():
    """Create web pages for the portals"""
    
    # Transport Portal Web Page
    if not frappe.db.exists("Web Page", "transport-portal"):
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
    else:
        print("ℹ️ Transport portal web page already exists")
    
    # Warehousing Portal Web Page
    if not frappe.db.exists("Web Page", "warehousing-portal"):
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
    else:
        print("ℹ️ Warehousing portal web page already exists")
    
    frappe.db.commit()
