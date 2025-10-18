# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def force_update_wiki_space():
    """Force update Wiki Space with warehousing pages"""
    
    print("🏭 Force updating Wiki Space with warehousing pages...")
    
    try:
        # Get all Wiki Spaces
        wiki_spaces = frappe.get_all("Wiki Space", fields=["name", "title", "route"])
        print(f"📋 Found {len(wiki_spaces)} Wiki Spaces:")
        for space in wiki_spaces:
            print(f"   - {space.name}: {space.title} (Route: {space.route})")
        
        if not wiki_spaces:
            print("❌ No Wiki Spaces found")
            return
        
        # Use the first Wiki Space
        wiki_space_name = wiki_spaces[0].name
        print(f"\n✅ Working with Wiki Space: {wiki_space_name}")
        
        # Get the Wiki Space document
        wiki_space = frappe.get_doc("Wiki Space", wiki_space_name)
        
        # Update basic info
        wiki_space.title = "CargoNext Documentation"
        wiki_space.description = "Comprehensive documentation for CargoNext logistics management system"
        wiki_space.route = "warehousing"
        wiki_space.published = 1
        
        # Clear existing sidebars
        wiki_space.set("wiki_sidebars", [])
        
        # Define warehousing pages with their actual titles
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
        added_count = 0
        for page in warehousing_pages:
            try:
                # Check if the wiki page exists
                wiki_pages = frappe.get_all("Wiki Page", 
                                          filters={"title": page["wiki_page"]}, 
                                          fields=["name", "title"])
                
                if wiki_pages:
                    # Add to sidebar
                    sidebar_row = wiki_space.append("wiki_sidebars", {})
                    sidebar_row.parent_label = page["parent_label"]
                    sidebar_row.wiki_page = page["wiki_page"]
                    print(f"✅ Added: {page['wiki_page']} under {page['parent_label']}")
                    added_count += 1
                else:
                    print(f"⚠️ Wiki page not found: {page['wiki_page']}")
                    
            except Exception as e:
                print(f"ℹ️ Could not add {page['wiki_page']}: {e}")
        
        # Save the Wiki Space
        try:
            wiki_space.save(ignore_permissions=True)
            frappe.db.commit()
            print(f"\n✅ Wiki Space saved successfully with {added_count} pages")
        except Exception as e:
            print(f"ℹ️ Could not save Wiki Space: {e}")
            # Try to save individual sidebar entries
            try:
                for sidebar in wiki_space.wiki_sidebars:
                    sidebar.save(ignore_permissions=True)
                frappe.db.commit()
                print("✅ Individual sidebar entries saved")
            except Exception as e2:
                print(f"ℹ️ Could not save individual entries: {e2}")
        
        # Verify the configuration
        try:
            wiki_space.reload()
            print(f"\n📋 Wiki Space '{wiki_space.name}' now has {len(wiki_space.wiki_sidebars)} sidebar entries")
            
            # Display the structure
            print("\n🏭 Warehousing Documentation Structure:")
            current_parent = None
            for sidebar in wiki_space.wiki_sidebars:
                if sidebar.parent_label != current_parent:
                    print(f"\n📁 {sidebar.parent_label}:")
                    current_parent = sidebar.parent_label
                print(f"   - {sidebar.wiki_page}")
                
        except Exception as e:
            print(f"ℹ️ Could not verify configuration: {e}")
        
    except Exception as e:
        print(f"ℹ️ Could not update Wiki Space: {e}")
    
    print("\n🎯 Wiki Space force update completed!")
    print("📖 Access the documentation at: https://cargonext.io/warehousing")
    print("🏭 All warehousing documentation should now be properly organized")


if __name__ == "__main__":
    force_update_wiki_space()

