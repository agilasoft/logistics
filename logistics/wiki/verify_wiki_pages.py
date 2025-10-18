import frappe

def verify_wiki_pages():
    """Verify existing wiki pages"""
    
    print("🔍 Verifying wiki pages...")
    
    # Get all wiki pages
    try:
        pages = frappe.get_all('Wiki Page', fields=['name', 'title', 'route', 'published'])
        print(f"📋 Found {len(pages)} wiki pages:")
        for page in pages:
            print(f"   - {page.name}: {page.title} (Route: {page.route}, Published: {page.published})")
    except Exception as e:
        print(f"ℹ️ Could not fetch wiki pages: {e}")
    
    # Check for warehousing-related pages
    warehousing_pages = [p for p in pages if 'warehouse' in p.title.lower() or 'warehousing' in p.title.lower() or 'vas' in p.title.lower() or 'billing' in p.title.lower() or 'sustainability' in p.title.lower()]
    print(f"\n🏭 Found {len(warehousing_pages)} warehousing-related pages:")
    for page in warehousing_pages:
        print(f"   - {page.name}: {page.title}")
    
    print(f"\n🎯 Wiki pages are accessible at:")
    print(f"   - Main Wiki: https://cargonext.io/wiki")
    print(f"   - Individual pages: https://cargonext.io/wiki/{page.name}")

if __name__ == "__main__":
    verify_wiki_pages()

