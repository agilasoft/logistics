#!/usr/bin/env python3

import sys
import os

# Add the frappe-bench directory to the path
sys.path.insert(0, '/home/frappe/frappe-bench')

# Set the site
os.environ['FRAPPE_SITE'] = 'cargonext.io'

import frappe
import json

def update_hero_section():
    try:
        # Initialize Frappe
        frappe.init(site='cargonext.io')
        frappe.connect()
        
        # Get the homepage web page
        web_pages = frappe.get_all("Web Page", 
                                 filters={"route": "/"}, 
                                 fields=["name", "content_type", "main_section"])
        
        if not web_pages:
            print("❌ No homepage found with route '/'")
            return
        
        web_page = web_pages[0]
        print(f"📄 Found homepage: {web_page.name}")
        
        if web_page.content_type != "Page Builder":
            print("❌ Web page is not using Page Builder content type")
            return
        
        try:
            page_builder_data = json.loads(web_page.main_section)
        except json.JSONDecodeError:
            print("❌ Could not parse Page Builder data")
            return
        
        # Find and update Hero with Image section
        updated = False
        for section in page_builder_data.get("sections", []):
            if section.get("section_type") == "Hero with Image":
                # Add semi-transparent box styling
                section["custom_css"] = """
                .hero-content {
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    border-radius: 20px;
                    padding: 3rem 2rem;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                    max-width: 800px;
                    margin: 0 auto;
                }
                
                .hero-content h1 {
                    color: #ffffff;
                    font-size: 3rem;
                    font-weight: 700;
                    margin-bottom: 1.5rem;
                    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
                }
                
                .hero-content p {
                    color: #ffffff;
                    font-size: 1.25rem;
                    opacity: 0.9;
                    margin-bottom: 2rem;
                    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
                }
                
                .hero-buttons {
                    display: flex;
                    gap: 1rem;
                    justify-content: center;
                    flex-wrap: wrap;
                }
                
                .btn-primary {
                    background: #ff6b00;
                    color: white;
                    padding: 1rem 2rem;
                    border-radius: 8px;
                    text-decoration: none;
                    font-weight: 600;
                    transition: all 0.3s ease;
                    border: none;
                }
                
                .btn-primary:hover {
                    background: #e55a00;
                    transform: translateY(-2px);
                    box-shadow: 0 8px 25px rgba(255, 107, 0, 0.3);
                }
                
                .btn-secondary {
                    background: transparent;
                    color: white;
                    border: 2px solid white;
                    padding: 1rem 2rem;
                    border-radius: 8px;
                    text-decoration: none;
                    font-weight: 600;
                    transition: all 0.3s ease;
                }
                
                .btn-secondary:hover {
                    background: white;
                    color: #2563eb;
                }
                
                @media (max-width: 768px) {
                    .hero-content {
                        padding: 2rem 1.5rem;
                        margin: 1rem;
                    }
                    
                    .hero-content h1 {
                        font-size: 2.5rem;
                    }
                    
                    .hero-buttons {
                        flex-direction: column;
                        align-items: center;
                    }
                    
                    .hero-buttons a {
                        width: 100%;
                        max-width: 300px;
                        text-align: center;
                    }
                }
                """
                updated = True
                print("✅ Added semi-transparent modern box styling to Hero section")
                break
        
        if not updated:
            print("❌ No Hero with Image section found")
            return
        
        # Save the updated web page
        doc = frappe.get_doc("Web Page", web_page.name)
        doc.main_section = json.dumps(page_builder_data)
        doc.save()
        frappe.db.commit()
        
        print("✅ Hero section updated successfully!")
        print("🎨 Applied modern glassmorphism design with:")
        print("   - Semi-transparent background (rgba(255, 255, 255, 0.1))")
        print("   - Backdrop blur effect")
        print("   - Rounded corners (20px)")
        print("   - Subtle border and shadow")
        print("   - Orange accent color (#ff6b00) for primary button")
        print("   - Responsive design for mobile devices")
        
    except Exception as e:
        print(f"❌ Error updating hero section: {str(e)}")
    
    finally:
        try:
            frappe.destroy()
        except:
            pass

if __name__ == "__main__":
    update_hero_section()
