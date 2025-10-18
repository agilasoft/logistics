# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def check_wiki_routes():
    """Check all wiki page routes and identify alignment issues"""
    
    print("🔍 Checking wiki page routes and alignment...")
    
    try:
        # Get all Wiki Pages
        pages = frappe.get_all('Wiki Page', fields=['name', 'title', 'route', 'published'])
        print(f"📚 Found {len(pages)} Wiki Pages:")
        
        route_issues = []
        alignment_issues = []
        
        for page in pages:
            print(f"\n📄 {page.title}")
            print(f"   Route: {page.route}")
            print(f"   Published: {page.published}")
            
            # Check for route alignment issues
            if page.route:
                # Check if route follows the expected pattern
                if not page.route.startswith('warehousing/'):
                    if page.title and 'warehousing' in page.title.lower():
                        route_issues.append({
                            'page': page.title,
                            'current_route': page.route,
                            'expected_route': f"warehousing/{page.route.split('/')[-1] if '/' in page.route else page.route}"
                        })
                        print(f"   ⚠️ Route alignment issue: {page.route}")
                
                # Check for inconsistent naming
                if page.route.startswith('warehousing/'):
                    route_name = page.route.replace('warehousing/', '')
                    if '-' in route_name and '_' in route_name:
                        alignment_issues.append({
                            'page': page.title,
                            'route': page.route,
                            'issue': 'Mixed naming convention'
                        })
                        print(f"   ⚠️ Naming convention issue: {page.route}")
        
        print(f"\n📊 Analysis Results:")
        print(f"   - Total pages: {len(pages)}")
        print(f"   - Route alignment issues: {len(route_issues)}")
        print(f"   - Naming convention issues: {len(alignment_issues)}")
        
        if route_issues:
            print(f"\n⚠️ Route alignment issues:")
            for issue in route_issues:
                print(f"   - {issue['page']}: {issue['current_route']} → {issue['expected_route']}")
        
        if alignment_issues:
            print(f"\n⚠️ Naming convention issues:")
            for issue in alignment_issues:
                print(f"   - {issue['page']}: {issue['route']} ({issue['issue']})")
        
        return route_issues, alignment_issues
        
    except Exception as e:
        print(f"ℹ️ Could not check wiki routes: {e}")
        return [], []


def fix_route_alignment():
    """Fix route alignment issues"""
    
    print("🔧 Fixing route alignment issues...")
    
    try:
        # Get all Wiki Pages
        pages = frappe.get_all('Wiki Page', fields=['name', 'title', 'route', 'published'])
        
        fixed_count = 0
        for page in pages:
            if page.route and not page.route.startswith('warehousing/'):
                if page.title and 'warehousing' in page.title.lower():
                    # Create new route
                    new_route = f"warehousing/{page.route.split('/')[-1] if '/' in page.route else page.route}"
                    
                    try:
                        # Update the route
                        frappe.db.set_value('Wiki Page', page.name, 'route', new_route)
                        print(f"✅ Fixed route for {page.title}: {page.route} → {new_route}")
                        fixed_count += 1
                    except Exception as e:
                        print(f"ℹ️ Could not fix route for {page.title}: {e}")
        
        frappe.db.commit()
        print(f"\n✅ Fixed {fixed_count} route alignment issues")
        
    except Exception as e:
        print(f"ℹ️ Could not fix route alignment: {e}")


def standardize_route_naming():
    """Standardize route naming conventions"""
    
    print("🔧 Standardizing route naming conventions...")
    
    try:
        # Get all Wiki Pages
        pages = frappe.get_all('Wiki Page', fields=['name', 'title', 'route', 'published'])
        
        fixed_count = 0
        for page in pages:
            if page.route and page.route.startswith('warehousing/'):
                route_name = page.route.replace('warehousing/', '')
                
                # Standardize to use hyphens consistently
                if '_' in route_name:
                    new_route_name = route_name.replace('_', '-')
                    new_route = f"warehousing/{new_route_name}"
                    
                    try:
                        # Update the route
                        frappe.db.set_value('Wiki Page', page.name, 'route', new_route)
                        print(f"✅ Standardized route for {page.title}: {page.route} → {new_route}")
                        fixed_count += 1
                    except Exception as e:
                        print(f"ℹ️ Could not standardize route for {page.title}: {e}")
        
        frappe.db.commit()
        print(f"\n✅ Standardized {fixed_count} route naming conventions")
        
    except Exception as e:
        print(f"ℹ️ Could not standardize route naming: {e}")


if __name__ == "__main__":
    route_issues, alignment_issues = check_wiki_routes()
    fix_route_alignment()
    standardize_route_naming()

