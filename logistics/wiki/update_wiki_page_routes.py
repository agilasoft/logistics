# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def update_wiki_page_routes():
    """Update Wiki Page routes to follow warehousing/wiki-name pattern"""
    
    print("🏭 Updating Wiki Page routes to warehousing/wiki-name pattern...")
    
    # Define the route mappings
    route_mappings = {
        "Warehousing Module - Complete User Guide": "warehousing/overview",
        "Warehouse Settings Configuration": "warehousing/warehouse-settings",
        "Storage Locations Setup": "warehousing/storage-locations",
        "Handling Unit Types Configuration": "warehousing/handling-unit-types",
        "Warehouse Jobs Operations": "warehousing/warehouse-jobs",
        "Value-Added Services (VAS) Operations": "warehousing/vas-operations",
        "Billing and Contracts Management": "warehousing/billing-contracts",
        "Sustainability and Reporting": "warehousing/sustainability",
        "Capacity Management": "warehousing/capacity-management",
        "Quality Management": "warehousing/quality-management",
        "Security and Compliance": "warehousing/security-compliance",
        "Automation and Integration": "warehousing/automation-integration",
        "Troubleshooting Guide": "warehousing/troubleshooting"
    }
    
    updated_count = 0
    
    for page_title, new_route in route_mappings.items():
        try:
            # Find the wiki page by title
            wiki_pages = frappe.get_all("Wiki Page", 
                                      filters={"title": page_title}, 
                                      fields=["name", "title", "route"])
            
            if wiki_pages:
                wiki_page = frappe.get_doc("Wiki Page", wiki_pages[0].name)
                old_route = wiki_page.route
                wiki_page.route = new_route
                wiki_page.save(ignore_permissions=True)
                print(f"✅ Updated {page_title}: {old_route} → {new_route}")
                updated_count += 1
            else:
                print(f"⚠️ Wiki page not found: {page_title}")
                
        except Exception as e:
            print(f"ℹ️ Could not update {page_title}: {e}")
    
    print(f"\n✅ Updated {updated_count} Wiki Page routes")
    print("🎯 All warehousing documentation now follows the warehousing/wiki-name route pattern")
    print("📖 Access examples:")
    print("   - Overview: https://cargonext.io/warehousing/overview")
    print("   - Warehouse Settings: https://cargonext.io/warehousing/warehouse-settings")
    print("   - Storage Locations: https://cargonext.io/warehousing/storage-locations")
    print("   - And so on...")


if __name__ == "__main__":
    update_wiki_page_routes()

