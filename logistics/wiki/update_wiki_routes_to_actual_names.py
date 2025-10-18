# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def update_wiki_routes_to_actual_names():
    """Update Wiki Page routes to use actual wiki page names"""
    
    print("🏭 Updating Wiki Page routes to use actual wiki page names...")
    
    # Define the route mappings using actual wiki page names
    route_mappings = {
        "Warehousing Module - Complete User Guide": "warehousing/warehousing-module-complete-user-guide",
        "Warehouse Settings Configuration": "warehousing/warehouse-settings-configuration",
        "Storage Locations Setup": "warehousing/storage-locations-setup",
        "Handling Unit Types Configuration": "warehousing/handling-unit-types-configuration",
        "Warehouse Jobs Operations": "warehousing/warehouse-jobs-operations",
        "Value-Added Services (VAS) Operations": "warehousing/value-added-services-vas-operations",
        "Billing and Contracts Management": "warehousing/billing-and-contracts-management",
        "Sustainability and Reporting": "warehousing/sustainability-and-reporting",
        "Capacity Management": "warehousing/capacity-management",
        "Quality Management": "warehousing/quality-management",
        "Security and Compliance": "warehousing/security-and-compliance",
        "Automation and Integration": "warehousing/automation-and-integration",
        "Troubleshooting Guide": "warehousing/troubleshooting-guide"
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
    print("🎯 All warehousing documentation now uses actual wiki page names in routes")
    print("📖 Access examples:")
    print("   - Overview: https://cargonext.io/warehousing/warehousing-module-complete-user-guide")
    print("   - Warehouse Settings: https://cargonext.io/warehousing/warehouse-settings-configuration")
    print("   - Storage Locations: https://cargonext.io/warehousing/storage-locations-setup")
    print("   - Warehouse Jobs: https://cargonext.io/warehousing/warehouse-jobs-operations")
    print("   - VAS Operations: https://cargonext.io/warehousing/value-added-services-vas-operations")
    print("   - Billing & Contracts: https://cargonext.io/warehousing/billing-and-contracts-management")
    print("   - Sustainability: https://cargonext.io/warehousing/sustainability-and-reporting")
    print("   - Capacity Management: https://cargonext.io/warehousing/capacity-management")
    print("   - Quality Management: https://cargonext.io/warehousing/quality-management")
    print("   - Security & Compliance: https://cargonext.io/warehousing/security-and-compliance")
    print("   - Automation & Integration: https://cargonext.io/warehousing/automation-and-integration")
    print("   - Troubleshooting: https://cargonext.io/warehousing/troubleshooting-guide")


if __name__ == "__main__":
    update_wiki_routes_to_actual_names()

