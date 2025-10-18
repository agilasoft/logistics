import frappe

def check_all_wiki_pages():
    """Check all wiki pages"""
    
    print("🔍 Checking all wiki pages...")
    
    try:
        pages = frappe.get_all('Wiki Page', fields=['name', 'title', 'route'])
        print(f"📚 Found {len(pages)} total Wiki Pages:")
        for page in pages:
            print(f"   - {page.name}: {page.title} (Route: {page.route})")
            
        # Check for warehousing-related pages
        warehousing_pages = [p for p in pages if any(keyword in p.title.lower() for keyword in ['warehouse', 'warehousing', 'vas', 'billing', 'sustainability', 'capacity', 'quality', 'security', 'automation', 'troubleshooting'])]
        print(f"\n🏭 Found {len(warehousing_pages)} warehousing-related pages:")
        for page in warehousing_pages:
            print(f"   - {page.title}")
            
    except Exception as e:
        print(f"ℹ️ Could not check wiki pages: {e}")

if __name__ == "__main__":
    check_all_wiki_pages()

