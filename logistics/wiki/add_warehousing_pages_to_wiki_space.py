# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def add_warehousing_pages_to_wiki_space():
    """Add warehousing pages to Wiki Space with Warehousing group"""
    
    print("🏭 Adding warehousing pages to Wiki Space...")
    
    # Get or create Wiki Space
    try:
        if frappe.db.exists("Wiki Space", "cargonext"):
            wiki_space = frappe.get_doc("Wiki Space", "cargonext")
            print("✅ Found existing Wiki Space: cargonext")
        else:
            # Create Wiki Space
            wiki_space = frappe.get_doc({
                "doctype": "Wiki Space",
                "name": "cargonext",
                "title": "CargoNext Documentation",
                "description": "Comprehensive documentation for CargoNext logistics management system",
                "route": "wiki",
                "published": 1
            })
            wiki_space.insert(ignore_permissions=True)
            print("✅ Created Wiki Space: cargonext")
    except Exception as e:
        print(f"ℹ️ Could not access Wiki Space: {e}")
        return
    
    # Clear existing sidebars
    wiki_space.set("wiki_sidebars", [])
    
    # Add warehousing pages with Warehousing group
    warehousing_pages = [
        {
            "parent_label": "Warehousing",
            "wiki_page": "Warehousing Module - Complete User Guide"
        },
        {
            "parent_label": "Warehousing",
            "wiki_page": "Warehouse Settings Configuration"
        },
        {
            "parent_label": "Warehousing",
            "wiki_page": "Storage Locations Setup"
        },
        {
            "parent_label": "Warehousing",
            "wiki_page": "Handling Unit Types Configuration"
        },
        {
            "parent_label": "Warehousing",
            "wiki_page": "Warehouse Jobs Operations"
        },
        {
            "parent_label": "Warehousing",
            "wiki_page": "Value-Added Services (VAS) Operations"
        },
        {
            "parent_label": "Warehousing",
            "wiki_page": "Billing and Contracts Management"
        },
        {
            "parent_label": "Warehousing",
            "wiki_page": "Sustainability and Reporting"
        },
        {
            "parent_label": "Warehousing",
            "wiki_page": "Capacity Management"
        },
        {
            "parent_label": "Warehousing",
            "wiki_page": "Quality Management"
        },
        {
            "parent_label": "Warehousing",
            "wiki_page": "Security and Compliance"
        },
        {
            "parent_label": "Warehousing",
            "wiki_page": "Automation and Integration"
        },
        {
            "parent_label": "Warehousing",
            "wiki_page": "Troubleshooting Guide"
        }
    ]
    
    # Add each page to the Wiki Space
    for page in warehousing_pages:
        try:
            # Check if the wiki page exists
            if frappe.db.exists("Wiki Page", {"title": page["wiki_page"]}):
                wiki_space.append("wiki_sidebars", {
                    "parent_label": page["parent_label"],
                    "wiki_page": page["wiki_page"]
                })
                print(f"✅ Added: {page['wiki_page']}")
            else:
                print(f"⚠️ Wiki page not found: {page['wiki_page']}")
        except Exception as e:
            print(f"ℹ️ Could not add {page['wiki_page']}: {e}")
    
    # Save the Wiki Space
    try:
        wiki_space.save(ignore_permissions=True)
        print(f"\n✅ Wiki Space saved with {len(wiki_space.wiki_sidebars)} warehousing pages")
        
        # Display the structure
        print("\n🏭 Warehousing Documentation Structure:")
        print("📁 Warehousing:")
        for sidebar in wiki_space.wiki_sidebars:
            if sidebar.parent_label == "Warehousing":
                print(f"   - {sidebar.wiki_page}")
        
    except Exception as e:
        print(f"ℹ️ Could not save Wiki Space: {e}")
    
    print("\n🎯 Warehousing pages have been added to Wiki Space!")
    print("📖 Access the documentation at: https://cargonext.io/wiki")
    print("🏭 All warehousing documentation is now organized under the 'Warehousing' group")


if __name__ == "__main__":
    add_warehousing_pages_to_wiki_space()

