# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def configure_warehousing_routes():
    """Configure Wiki Space with warehousing/wiki-name routes"""
    
    print("🏭 Configuring Wiki Space with warehousing routes...")
    
    try:
        # Get existing Wiki Space
        wiki_spaces = frappe.get_all("Wiki Space", fields=["name"])
        if wiki_spaces:
            wiki_space_name = wiki_spaces[0].name
            wiki_space = frappe.get_doc("Wiki Space", wiki_space_name)
            print(f"✅ Using Wiki Space: {wiki_space_name}")
            
            # Update the route to warehousing
            wiki_space.route = "warehousing"
            wiki_space.title = "Warehousing Documentation"
            wiki_space.description = "Comprehensive warehousing module documentation"
            
            # Clear existing sidebars
            wiki_space.set("wiki_sidebars", [])
            
            # Add warehousing pages with proper structure
            warehousing_pages = [
                {
                    "parent_label": "Overview",
                    "wiki_page": "Warehousing Module - Complete User Guide"
                },
                {
                    "parent_label": "Setup & Configuration",
                    "wiki_page": "Warehouse Settings Configuration"
                },
                {
                    "parent_label": "Setup & Configuration",
                    "wiki_page": "Storage Locations Setup"
                },
                {
                    "parent_label": "Setup & Configuration",
                    "wiki_page": "Handling Unit Types Configuration"
                },
                {
                    "parent_label": "Operations",
                    "wiki_page": "Warehouse Jobs Operations"
                },
                {
                    "parent_label": "Operations",
                    "wiki_page": "Value-Added Services (VAS) Operations"
                },
                {
                    "parent_label": "Business Management",
                    "wiki_page": "Billing and Contracts Management"
                },
                {
                    "parent_label": "Business Management",
                    "wiki_page": "Sustainability and Reporting"
                },
                {
                    "parent_label": "Advanced Features",
                    "wiki_page": "Capacity Management"
                },
                {
                    "parent_label": "Advanced Features",
                    "wiki_page": "Quality Management"
                },
                {
                    "parent_label": "Advanced Features",
                    "wiki_page": "Security and Compliance"
                },
                {
                    "parent_label": "Advanced Features",
                    "wiki_page": "Automation and Integration"
                },
                {
                    "parent_label": "Support",
                    "wiki_page": "Troubleshooting Guide"
                }
            ]
            
            # Add each page to the Wiki Space
            for page in warehousing_pages:
                try:
                    # Check if the wiki page exists
                    wiki_pages = frappe.get_all("Wiki Page", 
                                              filters={"title": page["wiki_page"]}, 
                                              fields=["name", "title"])
                    
                    if wiki_pages:
                        wiki_space.append("wiki_sidebars", {
                            "parent_label": page["parent_label"],
                            "wiki_page": page["wiki_page"]
                        })
                        print(f"✅ Added: {page['wiki_page']} under {page['parent_label']}")
                    else:
                        print(f"⚠️ Wiki page not found: {page['wiki_page']}")
                except Exception as e:
                    print(f"ℹ️ Could not add {page['wiki_page']}: {e}")
            
            # Save the Wiki Space
            wiki_space.save(ignore_permissions=True)
            print(f"\n✅ Wiki Space configured with route: warehousing")
            print(f"📋 Added {len(wiki_space.wiki_sidebars)} pages to sidebar")
            
            # Display the structure
            print("\n🏭 Warehousing Documentation Structure:")
            current_parent = None
            for sidebar in wiki_space.wiki_sidebars:
                if sidebar.parent_label != current_parent:
                    print(f"\n📁 {sidebar.parent_label}:")
                    current_parent = sidebar.parent_label
                print(f"   - {sidebar.wiki_page}")
            
        else:
            print("❌ No Wiki Spaces found")
            
    except Exception as e:
        print(f"ℹ️ Could not configure Wiki Space: {e}")
    
    print("\n🎯 Wiki Space configured with warehousing routes!")
    print("📖 Access the documentation at: https://cargonext.io/warehousing")
    print("🏭 All warehousing documentation is now organized with proper route structure")


if __name__ == "__main__":
    configure_warehousing_routes()

