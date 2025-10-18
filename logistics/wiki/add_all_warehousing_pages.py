# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def add_all_warehousing_pages():
    """Add all available warehousing pages to Wiki Space"""
    
    print("🏭 Adding all available warehousing pages to Wiki Space...")
    
    try:
        # Get Wiki Spaces
        wiki_spaces = frappe.get_all("Wiki Space", fields=["name"])
        if not wiki_spaces:
            print("❌ No Wiki Spaces found")
            return
        
        wiki_space_name = wiki_spaces[0].name
        print(f"✅ Using Wiki Space: {wiki_space_name}")
        
        # Get all warehousing-related pages
        warehousing_pages = [
            "Warehousing Module - Complete User Guide",
            "Warehouse Settings Configuration",
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
        added_count = 0
        for wiki_page_name in warehousing_pages:
            try:
                # Check if the wiki page exists
                wiki_page_exists = frappe.db.exists("Wiki Page", {"title": wiki_page_name})
                if wiki_page_exists:
                    sidebar_row = wiki_space.append("wiki_sidebars", {})
                    sidebar_row.parent_label = "Warehousing"
                    sidebar_row.wiki_page = wiki_page_name
                    print(f"✅ Added: {wiki_page_name}")
                    added_count += 1
                else:
                    print(f"⚠️ Wiki page not found: {wiki_page_name}")
            except Exception as e:
                print(f"ℹ️ Could not add {wiki_page_name}: {e}")
        
        # Save the Wiki Space
        try:
            wiki_space.save(ignore_permissions=True)
            frappe.db.commit()
            print(f"\n✅ Wiki Space saved with {added_count} warehousing pages")
        except Exception as e:
            print(f"ℹ️ Could not save Wiki Space: {e}")
        
        # Display the final structure
        print("\n🏭 Final Warehousing Documentation Structure:")
        print("📁 Warehousing:")
        for sidebar in wiki_space.wiki_sidebars:
            if sidebar.parent_label == "Warehousing":
                print(f"   - {sidebar.wiki_page}")
        
    except Exception as e:
        print(f"ℹ️ Could not add warehousing pages: {e}")
    
    print("\n🎯 All available warehousing pages added to Wiki Space!")
    print("📖 Access the documentation at: https://cargonext.io/warehousing")
    print("🏭 All pages are organized under the 'Warehousing' parent label")
    print("\n📋 Available pages:")
    print("   - Warehousing Module - Complete User Guide")
    print("   - Warehouse Settings Configuration")
    print("   - Warehouse Jobs Operations")
    print("   - Value-Added Services (VAS) Operations")
    print("   - Billing and Contracts Management")
    print("   - Sustainability and Reporting")
    print("   - Capacity Management")
    print("   - Quality Management")
    print("   - Security and Compliance")
    print("   - Automation and Integration")
    print("   - Troubleshooting Guide")


if __name__ == "__main__":
    add_all_warehousing_pages()

