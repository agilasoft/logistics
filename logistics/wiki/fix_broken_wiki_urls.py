# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def fix_broken_wiki_urls():
    """Fix broken Wiki Page URLs"""
    
    print("🔧 Fixing broken Wiki Page URLs...")
    
    try:
        # Get broken pages
        broken_pages = frappe.get_all('Wiki Page', 
                                    filters={'route': ['in', ['None/new-wiki-page', 'wiki/new-wiki-page']]}, 
                                    fields=['name', 'title', 'route'])
        
        print(f"❌ Found {len(broken_pages)} broken pages:")
        for page in broken_pages:
            print(f"   - {page.title} (Route: {page.route})")
        
        # Fix each broken page
        for page in broken_pages:
            try:
                wiki_page = frappe.get_doc("Wiki Page", page.name)
                
                # Generate proper route based on title
                if page.title == "New Wiki Page":
                    # Delete these placeholder pages
                    frappe.delete_doc("Wiki Page", page.name)
                    print(f"✅ Deleted placeholder page: {page.title}")
                else:
                    # Fix the route
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
        
        # Verify the fix
        remaining_broken = frappe.get_all('Wiki Page', 
                                        filters={'route': ['in', ['None/new-wiki-page', 'wiki/new-wiki-page']]}, 
                                        fields=['name', 'title', 'route'])
        
        if remaining_broken:
            print(f"⚠️ Still {len(remaining_broken)} broken pages remaining")
        else:
            print("✅ No broken pages remaining!")
        
    except Exception as e:
        print(f"ℹ️ Could not fix broken URLs: {e}")


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
    
    # Add warehousing prefix if not already present
    if not route.startswith("warehousing/") and not route.startswith("wiki/"):
        route = f"warehousing/{route}"
    
    return route


def verify_all_wiki_urls():
    """Verify all Wiki Page URLs are working"""
    
    print("🔍 Verifying all Wiki Page URLs...")
    
    try:
        # Get all Wiki Pages
        pages = frappe.get_all('Wiki Page', fields=['name', 'title', 'route', 'published'])
        
        print(f"📚 Checking {len(pages)} Wiki Pages:")
        
        valid_count = 0
        broken_count = 0
        
        for page in pages:
            if not page.route or page.route == "None" or "new-wiki-page" in page.route:
                print(f"   ❌ {page.title} (Route: {page.route})")
                broken_count += 1
            else:
                print(f"   ✅ {page.title} (Route: {page.route})")
                valid_count += 1
        
        print(f"\n📊 Summary:")
        print(f"   - Valid pages: {valid_count}")
        print(f"   - Broken pages: {broken_count}")
        
        if broken_count == 0:
            print("🎉 All Wiki Page URLs are working correctly!")
        else:
            print(f"⚠️ {broken_count} pages still have broken URLs")
        
    except Exception as e:
        print(f"ℹ️ Could not verify Wiki Page URLs: {e}")


if __name__ == "__main__":
    fix_broken_wiki_urls()
    verify_all_wiki_urls()

