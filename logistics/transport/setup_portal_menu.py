# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def setup_portal_menu_items():
    """Setup portal menu items for transport and warehousing portals"""
    
    # Transport Jobs Portal
    if not frappe.db.exists("Portal Menu Item", "Transport Jobs"):
        transport_menu = frappe.get_doc({
            "doctype": "Portal Menu Item",
            "title": "Transport Jobs",
            "route": "/transport-portal",
            "reference_doctype": "Transport Job",
            "icon": "fa fa-truck"
        })
        transport_menu.insert(ignore_permissions=True)
        print("✅ Transport Jobs portal menu item created")
    else:
        print("ℹ️ Transport Jobs portal menu item already exists")
    
    # Stock Balance Portal
    if not frappe.db.exists("Portal Menu Item", "Stock Balance"):
        stock_menu = frappe.get_doc({
            "doctype": "Portal Menu Item",
            "title": "Stock Balance",
            "route": "/warehousing-portal",
            "reference_doctype": "Stock Ledger Entry",
            "icon": "fa fa-warehouse"
        })
        stock_menu.insert(ignore_permissions=True)
        print("✅ Stock Balance portal menu item created")
    else:
        print("ℹ️ Stock Balance portal menu item already exists")
    
    # Create Web Pages for the portals
    create_web_pages()
    
    frappe.db.commit()
    print("✅ Portal menu items setup complete")


def create_web_pages():
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


def update_portal_settings():
    """Update portal settings to include the new portals"""
    
    # Get or create portal settings
    try:
        portal_settings = frappe.get_single("Portal Settings")
    except:
        # Create portal settings if it doesn't exist
        portal_settings = frappe.get_doc({
            "doctype": "Portal Settings",
            "default_portal_home": "/transport-portal"
        })
        portal_settings.insert(ignore_permissions=True)
        print("✅ Portal Settings created")
    
    # Update portal settings
    portal_settings.default_portal_home = "/transport-portal"
    portal_settings.save(ignore_permissions=True)
    print("✅ Portal Settings updated")
    
    frappe.db.commit()


if __name__ == "__main__":
    setup_portal_menu_items()
    update_portal_settings()
