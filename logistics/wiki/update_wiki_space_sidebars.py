# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def update_wiki_space_sidebars():
    """Update Wiki Space sidebars with warehousing pages"""
    
    print("🏭 Updating Wiki Space sidebars with warehousing pages...")
    
    try:
        # Get existing Wiki Space
        wiki_spaces = frappe.get_all("Wiki Space", fields=["name", "title"])
        print(f"📋 Found {len(wiki_spaces)} Wiki Spaces:")
        for space in wiki_spaces:
            print(f"   - {space.name}: {space.title}")
        
        # Use the first available Wiki Space
        if wiki_spaces:
            wiki_space_name = wiki_spaces[0].name
            wiki_space = frappe.get_doc("Wiki Space", wiki_space_name)
            print(f"✅ Using Wiki Space: {wiki_space_name}")
            
            # Clear existing sidebars
            wiki_space.set("wiki_sidebars", [])
            
            # Add warehousing pages
            warehousing_pages = [
                "Warehousing Module - Complete User Guide",
                "Warehouse Settings Configuration", 
                "Storage Locations Setup",
                "Handling Unit Types Configuration",
                "Warehouse Jobs Operations",
                "Value-Added Services (VAS) Operations",
                "Billing and Contracts Management",
                "Sustainability and Reporting",
                "Capacity Management",
                "Quality Management",
                "Security and Compliance",
                "Automation and Integration",
                "Troubleshooting Guide"
            ]
            
            # Add each page to the Wiki Space
            for page_title in warehousing_pages:
                try:
                    # Check if the wiki page exists
                    wiki_pages = frappe.get_all("Wiki Page", 
                                              filters={"title": page_title}, 
                                              fields=["name", "title"])
                    
                    if wiki_pages:
                        wiki_space.append("wiki_sidebars", {
                            "parent_label": "Warehousing",
                            "wiki_page": page_title
                        })
                        print(f"✅ Added: {page_title}")
                    else:
                        print(f"⚠️ Wiki page not found: {page_title}")
                except Exception as e:
                    print(f"ℹ️ Could not add {page_title}: {e}")
            
            # Save the Wiki Space
            wiki_space.save(ignore_permissions=True)
            print(f"\n✅ Wiki Space updated with {len(wiki_space.wiki_sidebars)} warehousing pages")
            
            # Display the structure
            print("\n🏭 Warehousing Documentation Structure:")
            print("📁 Warehousing:")
            for sidebar in wiki_space.wiki_sidebars:
                if sidebar.parent_label == "Warehousing":
                    print(f"   - {sidebar.wiki_page}")
            
        else:
            print("❌ No Wiki Spaces found")
            
    except Exception as e:
        print(f"ℹ️ Could not update Wiki Space: {e}")
    
    print("\n🎯 Warehousing pages have been added to Wiki Space!")
    print("📖 Access the documentation at: https://cargonext.io/wiki")
    print("🏭 All warehousing documentation is now organized under the 'Warehousing' group")


if __name__ == "__main__":
    update_wiki_space_sidebars()

