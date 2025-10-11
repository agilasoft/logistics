# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def setup_transport_portal():
    """Setup transport portal web page"""
    
    # Create Web Page for transport portal
    if not frappe.db.exists("Web Page", "transport-portal"):
        web_page = frappe.get_doc({
            "doctype": "Web Page",
            "title": "Transport Jobs Portal",
            "route": "/transport-portal",
            "published": 1,
            "content_type": "HTML",
            "main_section": '<div id="transport-portal-content"></div>',
            "meta_title": "Transport Jobs Portal",
            "meta_description": "Track your transport jobs and shipments"
        })
        web_page.insert(ignore_permissions=True)
        frappe.db.commit()
        print("✅ Transport portal web page created")
    else:
        print("ℹ️ Transport portal web page already exists")
    
    # Create Portal Menu Item
    if not frappe.db.exists("Portal Menu Item", "Transport Jobs"):
        portal_menu = frappe.get_doc({
            "doctype": "Portal Menu Item",
            "title": "Transport Jobs",
            "route": "/transport-portal",
            "reference_doctype": "Transport Job",
            "role": "Customer",
            "icon": "fa fa-truck"
        })
        portal_menu.insert(ignore_permissions=True)
        frappe.db.commit()
        print("✅ Portal menu item created")
    else:
        print("ℹ️ Portal menu item already exists")


if __name__ == "__main__":
    setup_transport_portal()
