# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def setup_web_pages():
    """Setup web pages for the portals"""
    
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
    print("✅ Web pages setup complete")


if __name__ == "__main__":
    setup_web_pages()
