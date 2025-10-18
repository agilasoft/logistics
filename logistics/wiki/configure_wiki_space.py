# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def configure_wiki_space():
    """Configure the Wiki Space for warehousing documentation"""
    
    print("🔧 Configuring Wiki Space for warehousing documentation...")
    
    # Check if Wiki Space exists
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
        print(f"ℹ️ Could not create/access Wiki Space: {e}")
        return
    
    # Configure Wiki Sidebars for warehousing documentation
    try:
        # Clear existing sidebars
        wiki_space.set("wiki_sidebars", [])
        
        # Add warehousing documentation to sidebar
        warehousing_sidebars = [
            {
                "parent_label": "Warehousing",
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
        
        for sidebar in warehousing_sidebars:
            wiki_space.append("wiki_sidebars", {
                "parent_label": sidebar["parent_label"],
                "wiki_page": sidebar["wiki_page"]
            })
        
        # Save the Wiki Space
        wiki_space.save(ignore_permissions=True)
        print("✅ Wiki Space configured with warehousing documentation")
        
    except Exception as e:
        print(f"ℹ️ Could not configure Wiki Space sidebars: {e}")
    
    # Verify the configuration
    try:
        wiki_space.reload()
        print(f"📋 Wiki Space '{wiki_space.name}' configured with {len(wiki_space.wiki_sidebars)} sidebar entries")
        
        print("\n🏭 Warehousing Documentation Structure:")
        current_parent = None
        for sidebar in wiki_space.wiki_sidebars:
            if sidebar.parent_label != current_parent:
                print(f"\n📁 {sidebar.parent_label}:")
                current_parent = sidebar.parent_label
            print(f"   - {sidebar.wiki_page}")
            
    except Exception as e:
        print(f"ℹ️ Could not verify Wiki Space configuration: {e}")
    
    print("\n🎯 Wiki Space is now configured and saved!")
    print("📖 Access the documentation at: https://cargonext.io/wiki")


if __name__ == "__main__":
    configure_wiki_space()

