#!/usr/bin/env python3
"""
Install House Airway Bill Print Format for Air Shipment
"""
import frappe
import os

def install_hawb_print_format():
    """Install or update the HAWB print format"""
    
    # Get the HTML content
    html_path = os.path.join(os.path.dirname(__file__), 'house_airway_bill.html')
    
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Check if print format exists
    if frappe.db.exists("Print Format", "House Airway Bill"):
        print_format = frappe.get_doc("Print Format", "House Airway Bill")
        print_format.html = html_content
        print_format.save()
        print("✓ Updated existing House Airway Bill print format")
    else:
        # Create new print format
        print_format = frappe.get_doc({
            "doctype": "Print Format",
            "name": "House Airway Bill",
            "doc_type": "Air Shipment",
            "module": "Air Freight",
            "standard": "No",
            "custom_format": 1,
            "print_format_type": "Jinja",
            "html": html_content,
            "font_size": 10,
            "disabled": 0,
            "align_labels_right": 0,
            "line_breaks": 0,
            "print_format_builder": 0,
            "raw_printing": 0,
            "show_section_headings": 0
        })
        print_format.insert(ignore_permissions=True)
        print("✓ Created new House Airway Bill print format")
    
    frappe.db.commit()
    print("✓ House Airway Bill print format installed successfully!")
    print("  You can now use it from Air Shipment > Print > House Airway Bill")

if __name__ == "__main__":
    import sys
    site = sys.argv[1] if len(sys.argv) > 1 else None
    if site:
        frappe.init(site=site)
        frappe.connect()
        install_hawb_print_format()
    else:
        print("Please provide a site name as argument")

