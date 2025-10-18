import frappe

def check_wiki_pages():
    """Check existing wiki pages and their spaces"""
    
    print("🔍 Checking wiki pages and spaces...")
    
    # Get all wiki pages
    pages = frappe.get_all('Wiki Page', fields=['name', 'title', 'space', 'published'])
    
    print(f"📋 Found {len(pages)} wiki pages:")
    for page in pages:
        print(f"   - {page.name}: {page.title} (Space: {page.space}, Published: {page.published})")
    
    # Check wiki spaces
    try:
        spaces = frappe.get_all('Wiki Space', fields=['name', 'title', 'published'])
        print(f"\n📁 Found {len(spaces)} wiki spaces:")
        for space in spaces:
            print(f"   - {space.name}: {space.title} (Published: {space.published})")
    except Exception as e:
        print(f"ℹ️ Could not fetch wiki spaces: {e}")
    
    # Check warehousing space specifically
    warehousing_pages = [p for p in pages if p.space == 'warehousing']
    print(f"\n🏭 Warehousing space has {len(warehousing_pages)} pages:")
    for page in warehousing_pages:
        print(f"   - {page.name}: {page.title}")

if __name__ == "__main__":
    check_wiki_pages()
