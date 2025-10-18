# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def check_wiki_space_structure():
    """Check the actual structure of Wiki Space"""
    
    print("🔍 Checking Wiki Space structure...")
    
    try:
        # Get Wiki Spaces
        wiki_spaces = frappe.get_all("Wiki Space", fields=["name"])
        print(f"📋 Found {len(wiki_spaces)} Wiki Spaces")
        
        if wiki_spaces:
            wiki_space_name = wiki_spaces[0].name
            print(f"✅ Using Wiki Space: {wiki_space_name}")
            
            # Get Wiki Space document
            wiki_space = frappe.get_doc("Wiki Space", wiki_space_name)
            print(f"📄 Wiki Space fields:")
            for field in wiki_space.meta.fields:
                if field.fieldtype in ["Table", "Section Break", "Column Break", "Tab Break"]:
                    print(f"   - {field.fieldname}: {field.fieldtype} ({field.label})")
            
            # Check if there are any child tables
            child_tables = [field for field in wiki_space.meta.fields if field.fieldtype == "Table"]
            print(f"\n📋 Child tables found: {len(child_tables)}")
            for table in child_tables:
                print(f"   - {table.fieldname}: {table.options}")
                
        # Check available Wiki Pages
        wiki_pages = frappe.get_all("Wiki Page", 
                                  filters={"title": ["like", "%warehousing%"]}, 
                                  fields=["name", "title", "route"])
        print(f"\n📚 Found {len(wiki_pages)} warehousing-related Wiki Pages:")
        for page in wiki_pages:
            print(f"   - {page.name}: {page.title} (Route: {page.route})")
            
    except Exception as e:
        print(f"ℹ️ Could not check Wiki Space structure: {e}")
    
    print("\n🎯 Manual steps needed:")
    print("1. Go to the Wiki Space configuration interface")
    print("2. Add the following pages to the sidebar:")
    print("   - Warehousing Module - Complete User Guide")
    print("   - Warehouse Settings Configuration")
    print("   - Storage Locations Setup")
    print("   - Handling Unit Types Configuration")
    print("   - Warehouse Jobs Operations")
    print("   - Value-Added Services (VAS) Operations")
    print("   - Billing and Contracts Management")
    print("   - Sustainability and Reporting")
    print("   - Capacity Management")
    print("   - Quality Management")
    print("   - Security and Compliance")
    print("   - Automation and Integration")
    print("   - Troubleshooting Guide")
    print("3. Save the Wiki Space configuration")


if __name__ == "__main__":
    check_wiki_space_structure()

