# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def shorten_wiki_routes():
    """Shorten Wiki Page routes to be more user-friendly"""
    
    print("🔧 Shortening Wiki Page routes...")
    
    # Define shorter routes for each page
    route_mappings = {
        "Warehousing Module - Complete User Guide": "warehousing/overview",
        "Warehouse Settings Configuration": "warehousing/settings",
        "Storage Locations Setup": "warehousing/locations",
        "Handling Unit Types Configuration": "warehousing/handling-units",
        "Warehouse Jobs Operations": "warehousing/jobs",
        "Value-Added Services (VAS) Operations": "warehousing/vas",
        "Billing and Contracts Management": "warehousing/billing",
        "Sustainability and Reporting": "warehousing/sustainability",
        "Capacity Management": "warehousing/capacity",
        "Quality Management": "warehousing/quality",
        "Security and Compliance": "warehousing/security",
        "Automation and Integration": "warehousing/automation",
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
    
    # Commit changes
    frappe.db.commit()
    print(f"\n✅ Updated {updated_count} Wiki Page routes with shorter URLs")
    
    # Display the new routes
    print("\n🏭 New Short Routes:")
    print("📁 Warehousing Documentation:")
    for page_title, route in route_mappings.items():
        print(f"   - {page_title}: {route}")
    
    print("\n🎯 Access Examples:")
    print("   - Overview: https://cargonext.io/warehousing/overview")
    print("   - Settings: https://cargonext.io/warehousing/settings")
    print("   - Jobs: https://cargonext.io/warehousing/jobs")
    print("   - VAS: https://cargonext.io/warehousing/vas")
    print("   - Billing: https://cargonext.io/warehousing/billing")
    print("   - And so on...")


if __name__ == "__main__":
    shorten_wiki_routes()

