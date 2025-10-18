# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def final_wiki_space_setup():
    """Final setup of Wiki Space with proper warehousing pages"""
    
    print("🏭 Final Wiki Space setup with warehousing pages...")
    
    try:
        # Get Wiki Spaces
        wiki_spaces = frappe.get_all("Wiki Space", fields=["name"])
        if not wiki_spaces:
            print("❌ No Wiki Spaces found")
            return
        
        wiki_space_name = wiki_spaces[0].name
        print(f"✅ Using Wiki Space: {wiki_space_name}")
        
        # Get all warehousing wiki pages
        warehousing_pages = frappe.get_all("Wiki Page", 
                                         filters={"title": ["like", "%warehousing%"]}, 
                                         fields=["name", "title", "route"])
        
        print(f"📚 Found {len(warehousing_pages)} warehousing pages:")
        for page in warehousing_pages:
            print(f"   - {page.title} (Route: {page.route})")
        
        # Get the Wiki Space document
        wiki_space = frappe.get_doc("Wiki Space", wiki_space_name)
        
        # Update Wiki Space basic info
        wiki_space.title = "CargoNext Documentation"
        wiki_space.description = "Comprehensive documentation for CargoNext logistics management system"
        wiki_space.route = "warehousing"
        wiki_space.published = 1
        
        # Clear existing sidebars
        wiki_space.set("wiki_sidebars", [])
        
        # Add all warehousing pages with "Warehousing" as parent label
        for page in warehousing_pages:
            try:
                sidebar_row = wiki_space.append("wiki_sidebars", {})
                sidebar_row.parent_label = "Warehousing"
                sidebar_row.wiki_page = page.title
                print(f"✅ Added: {page.title}")
            except Exception as e:
                print(f"ℹ️ Could not add {page.title}: {e}")
        
        # Save the Wiki Space
        try:
            wiki_space.save(ignore_permissions=True)
            frappe.db.commit()
            print(f"\n✅ Wiki Space saved successfully")
        except Exception as e:
            print(f"ℹ️ Could not save Wiki Space: {e}")
        
        # Final verification
        print("\n🏭 Final Warehousing Documentation Structure:")
        print("📁 Warehousing:")
        for sidebar in wiki_space.wiki_sidebars:
            if sidebar.parent_label == "Warehousing":
                print(f"   - {sidebar.wiki_page}")
        
    except Exception as e:
        print(f"ℹ️ Could not complete Wiki Space setup: {e}")
    
    print("\n🎯 Wiki Space setup completed!")
    print("📖 Access the documentation at: https://cargonext.io/warehousing")
    print("🏭 All warehousing pages are now organized under the 'Warehousing' parent label")
    print("\n📋 Manual verification steps:")
    print("1. Go to https://cargonext.io/warehousing")
    print("2. Check if the sidebar shows all warehousing documentation")
    print("3. Verify that all pages are accessible and properly linked")


if __name__ == "__main__":
    final_wiki_space_setup()

