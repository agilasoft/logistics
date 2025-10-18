# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def fix_route_alignment():
    """Fix route alignment for warehousing pages"""
    
    print("🔧 Fixing route alignment for warehousing pages...")
    
    try:
        # Define pages that need route alignment fixes
        route_fixes = [
            {
                'current_route': 'warehouse-setup-guide',
                'new_route': 'warehousing/setup-guide',
                'title': 'Warehouse Setup Guide'
            },
            {
                'current_route': 'getting-started-with-cargonext', 
                'new_route': 'warehousing/getting-started',
                'title': 'Getting Started with CargoNext'
            }
        ]
        
        fixed_count = 0
        for fix in route_fixes:
            try:
                # Find the page by current route
                page = frappe.get_doc('Wiki Page', {'route': fix['current_route']})
                
                # Update the route
                page.route = fix['new_route']
                page.save(ignore_permissions=True)
                
                print(f"✅ Fixed route for {fix['title']}: {fix['current_route']} → {fix['new_route']}")
                fixed_count += 1
                
            except Exception as e:
                print(f"ℹ️ Could not fix route for {fix['title']}: {e}")
        
        frappe.db.commit()
        print(f"\n✅ Fixed {fixed_count} route alignment issues")
        
    except Exception as e:
        print(f"ℹ️ Could not fix route alignment: {e}")


def verify_route_alignment():
    """Verify all routes are properly aligned"""
    
    print("🔍 Verifying route alignment...")
    
    try:
        # Get all Wiki Pages
        pages = frappe.get_all('Wiki Page', fields=['name', 'title', 'route', 'published'])
        
        warehousing_pages = []
        other_pages = []
        
        for page in pages:
            if page.route.startswith('warehousing/'):
                warehousing_pages.append(page)
            else:
                other_pages.append(page)
        
        print(f"\n📊 Route Alignment Summary:")
        print(f"   - Warehousing pages: {len(warehousing_pages)}")
        print(f"   - Other pages: {len(other_pages)}")
        
        print(f"\n🏭 Warehousing Pages:")
        for page in warehousing_pages:
            print(f"   ✅ {page.title}: {page.route}")
        
        print(f"\n📄 Other Pages:")
        for page in other_pages:
            print(f"   ℹ️ {page.title}: {page.route}")
        
        return warehousing_pages, other_pages
        
    except Exception as e:
        print(f"ℹ️ Could not verify route alignment: {e}")
        return [], []


if __name__ == "__main__":
    fix_route_alignment()
    verify_route_alignment()

