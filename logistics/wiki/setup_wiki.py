# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def setup_wiki():
    """Setup wiki functionality for CargoNext"""
    
    print("🚀 Setting up Wiki for CargoNext...")
    
    # Create wiki web pages
    create_wiki_web_pages()
    
    # Create wiki space
    create_wiki_space()
    
    # Create sample wiki pages
    create_sample_wiki_pages()
    
    print("✅ Wiki setup complete!")
    print("📋 Wiki is now available at:")
    print("   - Main Wiki: /wiki")
    print("   - Wiki Space: /wiki/space/cargonext")
    print("🎉 Wiki installation complete!")


def create_wiki_web_pages():
    """Create web pages for wiki functionality"""
    
    # Main Wiki Page
    if not frappe.db.exists("Web Page", "wiki"):
        wiki_page = frappe.get_doc({
            "doctype": "Web Page",
            "title": "CargoNext Wiki",
            "route": "/wiki",
            "published": 1,
            "content_type": "HTML",
            "main_section": '''
            <div class="wiki-container">
                <div class="wiki-header">
                    <h1>Welcome to CargoNext Wiki</h1>
                    <p>Your comprehensive guide to CargoNext logistics management system</p>
                </div>
                <div class="wiki-content">
                    <div class="wiki-navigation">
                        <h3>Quick Navigation</h3>
                        <ul>
                            <li><a href="/wiki/space/cargonext">CargoNext Documentation</a></li>
                            <li><a href="/wiki/space/warehousing">Warehousing Guide</a></li>
                            <li><a href="/wiki/space/transport">Transport Management</a></li>
                            <li><a href="/wiki/space/freight">Freight Operations</a></li>
                            <li><a href="/wiki/space/pricing">Pricing Center</a></li>
                        </ul>
                    </div>
                    <div class="wiki-features">
                        <h3>What's Available</h3>
                        <ul>
                            <li>📚 Comprehensive documentation</li>
                            <li>🔍 Search functionality</li>
                            <li>📝 Collaborative editing</li>
                            <li>🏷️ Category organization</li>
                            <li>📊 Version history</li>
                        </ul>
                    </div>
                </div>
            </div>
            <style>
                .wiki-container {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }
                .wiki-header {
                    text-align: center;
                    margin-bottom: 40px;
                    padding: 40px 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border-radius: 10px;
                }
                .wiki-content {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 40px;
                    margin-top: 30px;
                }
                .wiki-navigation, .wiki-features {
                    background: #f8f9fa;
                    padding: 30px;
                    border-radius: 8px;
                    border-left: 4px solid #667eea;
                }
                .wiki-navigation ul, .wiki-features ul {
                    list-style: none;
                    padding: 0;
                }
                .wiki-navigation li, .wiki-features li {
                    padding: 10px 0;
                    border-bottom: 1px solid #e9ecef;
                }
                .wiki-navigation a {
                    color: #667eea;
                    text-decoration: none;
                    font-weight: 500;
                }
                .wiki-navigation a:hover {
                    text-decoration: underline;
                }
            </style>
            ''',
            "meta_title": "CargoNext Wiki - Documentation & Help",
            "meta_description": "Comprehensive documentation and help for CargoNext logistics management system"
        })
        wiki_page.insert(ignore_permissions=True)
        print("✅ Main wiki web page created")
    else:
        print("ℹ️ Main wiki web page already exists")
    
    # Wiki Space Pages
    create_wiki_space_pages()
    
    frappe.db.commit()


def create_wiki_space_pages():
    """Create wiki space pages"""
    
    spaces = [
        {
            "name": "cargonext",
            "title": "CargoNext Documentation",
            "route": "/wiki/space/cargonext",
            "description": "Main documentation for CargoNext logistics system"
        },
        {
            "name": "warehousing",
            "title": "Warehousing Guide",
            "route": "/wiki/space/warehousing",
            "description": "Complete guide to warehouse management features"
        },
        {
            "name": "transport",
            "title": "Transport Management",
            "route": "/wiki/space/transport",
            "description": "Transport job management and vehicle tracking"
        },
        {
            "name": "freight",
            "title": "Freight Operations",
            "route": "/wiki/space/freight",
            "description": "Air and sea freight operations guide"
        },
        {
            "name": "pricing",
            "title": "Pricing Center",
            "route": "/wiki/space/pricing",
            "description": "Rate calculation and pricing management"
        }
    ]
    
    for space in spaces:
        if not frappe.db.exists("Web Page", f"wiki-space-{space['name']}"):
            space_page = frappe.get_doc({
                "doctype": "Web Page",
                "title": space["title"],
                "route": space["route"],
                "published": 1,
                "content_type": "HTML",
                "main_section": f'''
                <div class="wiki-space-container">
                    <div class="wiki-space-header">
                        <h1>{space["title"]}</h1>
                        <p>{space["description"]}</p>
                    </div>
                    <div class="wiki-space-content">
                        <div class="wiki-space-nav">
                            <h3>Space Navigation</h3>
                            <ul>
                                <li><a href="/wiki">← Back to Wiki Home</a></li>
                                <li><a href="/wiki/space/cargonext">CargoNext Documentation</a></li>
                                <li><a href="/wiki/space/warehousing">Warehousing Guide</a></li>
                                <li><a href="/wiki/space/transport">Transport Management</a></li>
                                <li><a href="/wiki/space/freight">Freight Operations</a></li>
                                <li><a href="/wiki/space/pricing">Pricing Center</a></li>
                            </ul>
                        </div>
                        <div class="wiki-space-articles">
                            <h3>Articles in this Space</h3>
                            <div class="article-list">
                                <div class="article-item">
                                    <h4>Getting Started</h4>
                                    <p>Learn the basics of {space["title"].lower()}</p>
                                </div>
                                <div class="article-item">
                                    <h4>Configuration Guide</h4>
                                    <p>Step-by-step setup instructions</p>
                                </div>
                                <div class="article-item">
                                    <h4>Best Practices</h4>
                                    <p>Tips and recommendations for optimal usage</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <style>
                    .wiki-space-container {{
                        max-width: 1200px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .wiki-space-header {{
                        text-align: center;
                        margin-bottom: 40px;
                        padding: 30px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        border-radius: 10px;
                    }}
                    .wiki-space-content {{
                        display: grid;
                        grid-template-columns: 300px 1fr;
                        gap: 40px;
                        margin-top: 30px;
                    }}
                    .wiki-space-nav, .wiki-space-articles {{
                        background: #f8f9fa;
                        padding: 30px;
                        border-radius: 8px;
                        border-left: 4px solid #667eea;
                    }}
                    .wiki-space-nav ul {{
                        list-style: none;
                        padding: 0;
                    }}
                    .wiki-space-nav li {{
                        padding: 8px 0;
                        border-bottom: 1px solid #e9ecef;
                    }}
                    .wiki-space-nav a {{
                        color: #667eea;
                        text-decoration: none;
                        font-weight: 500;
                    }}
                    .wiki-space-nav a:hover {{
                        text-decoration: underline;
                    }}
                    .article-list {{
                        margin-top: 20px;
                    }}
                    .article-item {{
                        background: white;
                        padding: 20px;
                        margin-bottom: 15px;
                        border-radius: 5px;
                        border: 1px solid #e9ecef;
                    }}
                    .article-item h4 {{
                        margin: 0 0 10px 0;
                        color: #333;
                    }}
                    .article-item p {{
                        margin: 0;
                        color: #666;
                    }}
                </style>
                ''',
                "meta_title": f"{space['title']} - CargoNext Wiki",
                "meta_description": space["description"]
            })
            space_page.insert(ignore_permissions=True)
            print(f"✅ Wiki space '{space['name']}' created")
        else:
            print(f"ℹ️ Wiki space '{space['name']}' already exists")


def create_wiki_space():
    """Create wiki space in the system"""
    try:
        # Check if Wiki Space doctype exists
        if frappe.db.exists("DocType", "Wiki Space"):
            # Create main CargoNext wiki space
            if not frappe.db.exists("Wiki Space", "cargonext"):
                wiki_space = frappe.get_doc({
                    "doctype": "Wiki Space",
                    "name": "cargonext",
                    "title": "CargoNext Documentation",
                    "description": "Main documentation space for CargoNext logistics management system",
                    "published": 1
                })
                wiki_space.insert(ignore_permissions=True)
                print("✅ Wiki space 'cargonext' created")
            else:
                print("ℹ️ Wiki space 'cargonext' already exists")
        else:
            print("ℹ️ Wiki Space doctype not found - using web pages instead")
    except Exception as e:
        print(f"ℹ️ Could not create wiki space: {e}")


def create_sample_wiki_pages():
    """Create sample wiki pages"""
    try:
        # Check if Wiki Page doctype exists
        if frappe.db.exists("DocType", "Wiki Page"):
            sample_pages = [
                {
                    "name": "getting-started",
                    "title": "Getting Started with CargoNext",
                    "content": """
# Getting Started with CargoNext

Welcome to CargoNext, your comprehensive logistics management system!

## What is CargoNext?

CargoNext is a modern, integrated logistics management platform designed to streamline and optimize logistics operations across warehousing, transportation, and freight management.

## Key Features

- **Warehouse Management**: Complete warehouse operations including job management, storage tracking, and inventory control
- **Transportation Management**: End-to-end transport job lifecycle with route optimization and vehicle tracking
- **Freight Management**: Air and sea freight operations with IATA compliance and customs integration
- **Pricing Center**: Advanced rate calculation engine with flexible tariff management

## Quick Start Guide

1. **Setup**: Configure your warehouse locations and transport settings
2. **Users**: Add team members and assign appropriate roles
3. **Data**: Import your existing customer and item data
4. **Operations**: Start creating transport jobs and warehouse operations

## Need Help?

- Check our [FAQ section](/wiki/space/cargonext/faq)
- Contact support at support@cargonext.io
- Join our community forum
                    """,
                    "space": "cargonext"
                },
                {
                    "name": "warehouse-setup",
                    "title": "Warehouse Setup Guide",
                    "content": """
# Warehouse Setup Guide

This guide will help you set up your warehouse operations in CargoNext.

## Prerequisites

- Warehouse locations configured
- Storage types defined
- Handling unit types set up

## Step-by-Step Setup

### 1. Configure Warehouse Locations

1. Go to **Warehouse** > **Warehouse**
2. Create your warehouse locations
3. Define storage areas and zones

### 2. Set Up Storage Types

1. Navigate to **Warehouse** > **Storage Type**
2. Define different storage types (Bulk, Pallet, etc.)
3. Configure capacity and handling requirements

### 3. Create Handling Units

1. Go to **Warehouse** > **Handling Unit Type**
2. Define unit types (Container, Pallet, etc.)
3. Set capacity and tracking parameters

## Best Practices

- Organize storage by product type
- Implement proper labeling systems
- Regular inventory audits
- Maintain accurate capacity data
                    """,
                    "space": "warehousing"
                }
            ]
            
            for page_data in sample_pages:
                if not frappe.db.exists("Wiki Page", page_data["name"]):
                    wiki_page = frappe.get_doc({
                        "doctype": "Wiki Page",
                        "name": page_data["name"],
                        "title": page_data["title"],
                        "content": page_data["content"],
                        "space": page_data["space"],
                        "published": 1
                    })
                    wiki_page.insert(ignore_permissions=True)
                    print(f"✅ Sample wiki page '{page_data['name']}' created")
                else:
                    print(f"ℹ️ Sample wiki page '{page_data['name']}' already exists")
        else:
            print("ℹ️ Wiki Page doctype not found - using web pages instead")
    except Exception as e:
        print(f"ℹ️ Could not create sample wiki pages: {e}")


if __name__ == "__main__":
    setup_wiki()

