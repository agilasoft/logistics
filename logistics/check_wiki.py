import frappe

def check_wiki_pages():
    """Check if wiki pages were created successfully"""
    
    print("🔍 Checking wiki pages...")
    
    # Get all web pages with wiki routes
    pages = frappe.get_all('Web Page', 
                          filters={'route': ['like', '%wiki%']}, 
                          fields=['name', 'title', 'route', 'published'])
    
    print(f"📋 Found {len(pages)} wiki-related pages:")
    for page in pages:
        print(f"   - {page.name}: {page.title} ({page.route}) - Published: {page.published}")
    
    # Check if main wiki page exists
    if frappe.db.exists("Web Page", "wiki"):
        print("✅ Main wiki page exists")
    else:
        print("❌ Main wiki page not found")
    
    # Check wiki spaces
    spaces = ['cargonext', 'warehousing', 'transport', 'freight', 'pricing']
    for space in spaces:
        if frappe.db.exists("Web Page", f"wiki-space-{space}"):
            print(f"✅ Wiki space '{space}' exists")
        else:
            print(f"❌ Wiki space '{space}' not found")
    
    print("\n🎯 Wiki should be accessible at:")
    print("   - Main Wiki: https://cargonext.io/wiki")
    print("   - Wiki Spaces: https://cargonext.io/wiki/space/cargonext")

if __name__ == "__main__":
    check_wiki_pages()
