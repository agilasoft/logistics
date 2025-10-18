# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def review_wiki_content():
    """Review all wiki content for missing links and guides"""
    
    print("🔍 Reviewing all wiki content for missing links and guides...")
    
    try:
        # Get all Wiki Pages
        pages = frappe.get_all('Wiki Page', fields=['name', 'title', 'route', 'content'])
        print(f"📚 Found {len(pages)} Wiki Pages:")
        
        missing_guides = []
        broken_links = []
        
        for page in pages:
            print(f"\n📄 {page.title} ({page.route})")
            
            # Check content for missing links
            if page.content:
                content = page.content
                
                # Look for markdown links that might be broken
                import re
                links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
                for link_text, link_url in links:
                    if link_url.startswith('./') or link_url.startswith('/'):
                        # Check if the linked page exists
                        if not check_if_page_exists(link_url, pages):
                            broken_links.append({
                                'page': page.title,
                                'link_text': link_text,
                                'link_url': link_url
                            })
                            print(f"   ❌ Broken link: [{link_text}]({link_url})")
                
                # Check for missing guides mentioned in content
                if 'missing' in content.lower() or 'todo' in content.lower():
                    print(f"   ⚠️ Contains 'missing' or 'todo' references")
            
            # Check if this is a placeholder or incomplete page
            if not page.content or len(page.content) < 100:
                missing_guides.append(page.title)
                print(f"   ⚠️ Incomplete or missing content")
        
        # Check for expected guides that might be missing
        expected_guides = [
            "Inbound Operations",
            "Outbound Operations", 
            "Transfer Operations",
            "Periodic Billing",
            "Charges Management",
            "Customer Management",
            "Reporting and Analytics",
            "Best Practices",
            "Integration Guide"
        ]
        
        existing_titles = [page['title'] for page in pages]
        missing_expected = [guide for guide in expected_guides if guide not in existing_titles]
        
        print(f"\n📊 Analysis Results:")
        print(f"   - Total pages: {len(pages)}")
        print(f"   - Incomplete pages: {len(missing_guides)}")
        print(f"   - Broken links: {len(broken_links)}")
        print(f"   - Missing expected guides: {len(missing_expected)}")
        
        if missing_guides:
            print(f"\n⚠️ Incomplete pages:")
            for guide in missing_guides:
                print(f"   - {guide}")
        
        if broken_links:
            print(f"\n❌ Broken links:")
            for link in broken_links:
                print(f"   - {link['page']}: [{link['link_text']}]({link['link_url']})")
        
        if missing_expected:
            print(f"\n📝 Missing expected guides:")
            for guide in missing_expected:
                print(f"   - {guide}")
        
        return missing_guides, broken_links, missing_expected
        
    except Exception as e:
        print(f"ℹ️ Could not review wiki content: {e}")
        return [], [], []


def check_if_page_exists(link_url, pages):
    """Check if a linked page exists"""
    
    # Extract page name from URL
    if link_url.startswith('./'):
        page_name = link_url[2:]  # Remove './'
    elif link_url.startswith('/'):
        page_name = link_url[1:]  # Remove '/'
    else:
        page_name = link_url
    
    # Check if page exists
    for page in pages:
        if page['route'] == page_name or page['title'].lower() == page_name.lower():
            return True
    
    return False


def create_missing_guides():
    """Create missing guides that are commonly needed"""
    
    print("📝 Creating missing guides...")
    
    missing_guides = [
        {
            "name": "inbound-operations",
            "title": "Inbound Operations",
            "content": """# Inbound Operations

## Overview
Inbound operations handle the receiving and processing of incoming shipments and materials.

## Key Processes

### Receiving
- **Documentation Review**: Check shipping documents
- **Physical Inspection**: Inspect items for damage
- **Quantity Verification**: Verify received quantities
- **Quality Control**: Perform quality checks

### Putaway
- **Location Assignment**: Assign storage locations
- **Inventory Update**: Update inventory records
- **Labeling**: Apply location labels
- **Documentation**: Complete putaway documentation

## Best Practices
- Verify all documentation before receiving
- Inspect items immediately upon arrival
- Update inventory records in real-time
- Maintain accurate location records
"""
        },
        {
            "name": "outbound-operations", 
            "title": "Outbound Operations",
            "content": """# Outbound Operations

## Overview
Outbound operations handle the picking, packing, and shipping of customer orders.

## Key Processes

### Picking
- **Order Review**: Review customer orders
- **Location Planning**: Plan picking routes
- **Item Collection**: Collect items from locations
- **Quality Check**: Verify picked items

### Packing
- **Packaging Selection**: Choose appropriate packaging
- **Item Protection**: Protect items during packing
- **Labeling**: Apply shipping labels
- **Documentation**: Complete packing documentation

## Best Practices
- Optimize picking routes for efficiency
- Use appropriate packaging materials
- Verify all items before packing
- Maintain accurate shipping records
"""
        },
        {
            "name": "periodic-billing",
            "title": "Periodic Billing",
            "content": """# Periodic Billing

## Overview
Periodic billing automatically generates invoices for warehouse services based on usage and contracts.

## Billing Components

### Storage Charges
- **Volume-based**: Charges based on storage volume
- **Weight-based**: Charges based on weight
- **Time-based**: Charges based on storage duration
- **Location-based**: Charges based on storage location

### Handling Charges
- **Inbound Processing**: Charges for receiving services
- **Outbound Processing**: Charges for shipping services
- **Transfer Services**: Charges for internal transfers
- **Special Handling**: Charges for special requirements

## Configuration
1. **Billing Periods**: Set up billing cycles
2. **Charge Rates**: Configure charge rates
3. **Customer Contracts**: Link to customer agreements
4. **Automation**: Enable automatic billing

## Best Practices
- Review billing data before generating invoices
- Maintain accurate usage records
- Communicate charges clearly to customers
- Process billing on schedule
"""
        }
    ]
    
    created_count = 0
    for guide in missing_guides:
        try:
            if not frappe.db.exists("Wiki Page", guide["name"]):
                wiki_page = frappe.get_doc({
                    "doctype": "Wiki Page",
                    "name": guide["name"],
                    "title": guide["title"],
                    "content": guide["content"],
                    "route": f"warehousing/{guide['name']}",
                    "published": 1
                })
                wiki_page.insert(ignore_permissions=True)
                print(f"✅ Created: {guide['title']}")
                created_count += 1
            else:
                print(f"ℹ️ Already exists: {guide['title']}")
        except Exception as e:
            print(f"ℹ️ Could not create {guide['title']}: {e}")
    
    frappe.db.commit()
    print(f"\n✅ Created {created_count} missing guides")


if __name__ == "__main__":
    missing_guides, broken_links, missing_expected = review_wiki_content()
    create_missing_guides()

