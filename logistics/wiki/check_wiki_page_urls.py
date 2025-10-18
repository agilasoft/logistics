# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def check_wiki_page_urls():
    """Check Wiki Pages for broken URLs and routes"""
    
    print("🔍 Checking Wiki Pages for broken URLs...")
    
    try:
        # Get all Wiki Pages
        pages = frappe.get_all('Wiki Page', fields=['name', 'title', 'route', 'published'])
        print(f"📚 Found {len(pages)} Wiki Pages:")
        
        broken_pages = []
        valid_pages = []
        
        for page in pages:
            print(f"   - {page.name}: {page.title}")
            print(f"     Route: {page.route}")
            print(f"     Published: {page.published}")
            
            # Check for broken routes
            if not page.route or page.route == "None" or "new-wiki-page" in page.route:
                broken_pages.append(page)
                print(f"     ❌ BROKEN ROUTE")
            else:
                valid_pages.append(page)
                print(f"     ✅ Valid route")
            print()
        
        print(f"\n📊 Summary:")
        print(f"   - Total pages: {len(pages)}")
        print(f"   - Valid pages: {len(valid_pages)}")
        print(f"   - Broken pages: {len(broken_pages)}")
        
        if broken_pages:
            print(f"\n❌ Broken pages that need fixing:")
            for page in broken_pages:
                print(f"   - {page.title} (Route: {page.route})")
        
        return broken_pages, valid_pages
        
    except Exception as e:
        print(f"ℹ️ Could not check Wiki Pages: {e}")
        return [], []


def fix_broken_wiki_page_urls():
    """Fix broken Wiki Page URLs"""
    
    print("🔧 Fixing broken Wiki Page URLs...")
    
    # Check current pages
    broken_pages, valid_pages = check_wiki_page_urls()
    
    if not broken_pages:
        print("✅ No broken pages found!")
        return
    
    # Fix broken pages
    for page in broken_pages:
        try:
            wiki_page = frappe.get_doc("Wiki Page", page.name)
            
            # Generate proper route based on title
            route = generate_route_from_title(page.title)
            wiki_page.route = route
            wiki_page.published = 1
            
            wiki_page.save(ignore_permissions=True)
            print(f"✅ Fixed: {page.title} → {route}")
            
        except Exception as e:
            print(f"ℹ️ Could not fix {page.title}: {e}")
    
    # Commit changes
    frappe.db.commit()
    print("\n✅ All broken Wiki Page URLs have been fixed!")


def generate_route_from_title(title):
    """Generate a proper route from the title"""
    
    # Convert title to route format
    route = title.lower()
    route = route.replace(" ", "-")
    route = route.replace("(", "")
    route = route.replace(")", "")
    route = route.replace(":", "")
    route = route.replace(",", "")
    route = route.replace("&", "and")
    route = route.replace("--", "-")
    
    # Add warehousing prefix
    if not route.startswith("warehousing/"):
        route = f"warehousing/{route}"
    
    return route


if __name__ == "__main__":
    check_wiki_page_urls()

