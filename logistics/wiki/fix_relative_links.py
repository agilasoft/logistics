# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def fix_relative_links():
    """Fix all relative links to use proper routes"""
    
    print("🔗 Fixing relative links to use proper routes...")
    
    # Define the correct link mappings from relative to full routes
    link_mappings = {
        "./settings": "warehousing/settings",
        "./locations": "warehousing/locations", 
        "./handling-units": "warehousing/handling-units",
        "./jobs": "warehousing/jobs",
        "./vas": "warehousing/vas",
        "./billing": "warehousing/billing",
        "./capacity": "warehousing/capacity",
        "./quality": "warehousing/quality",
        "./sustainability": "warehousing/sustainability",
        "./security": "warehousing/security",
        "./troubleshooting": "warehousing/troubleshooting",
        "./inbound-operations": "warehousing/inbound-operations",
        "./outbound-operations": "warehousing/outbound-operations",
        "./periodic-billing": "warehousing/periodic-billing",
        "./charges": "warehousing/charges-management",
        "./customer": "warehousing/customer-management",
        "./reporting-analytics": "warehousing/reporting-analytics",
        "./best-practices": "warehousing/best-practices",
        "./integration-guide": "warehousing/integration-guide",
        "./automation": "warehousing/automation",
        "./transfer-operations": "warehousing/transfer-operations"
    }
    
    # Get all wiki pages
    pages = frappe.get_all('Wiki Page', fields=['name', 'title', 'route', 'content'])
    
    updated_count = 0
    for page in pages:
        if page.content:
            content = page.content
            original_content = content
            
            # Replace all relative links with full routes
            for relative_link, full_route in link_mappings.items():
                content = content.replace(relative_link, full_route)
            
            # If content was updated, save it
            if content != original_content:
                try:
                    frappe.db.set_value('Wiki Page', page.name, 'content', content)
                    print(f"✅ Fixed links in: {page.title}")
                    updated_count += 1
                except Exception as e:
                    print(f"ℹ️ Could not update {page.title}: {e}")
    
    frappe.db.commit()
    print(f"\n✅ Fixed relative links in {updated_count} pages")


if __name__ == "__main__":
    fix_relative_links()

