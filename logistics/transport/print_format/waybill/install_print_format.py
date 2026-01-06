#!/usr/bin/env python3
"""
Install Waybill Print Format for Transport Leg
"""
import frappe
import os

def install_waybill_print_format():
    """Install or update the Waybill print format"""
    
    # Get the HTML content
    html_path = os.path.join(os.path.dirname(__file__), 'waybill.html')
    
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Check if print format exists
    if frappe.db.exists("Print Format", "Waybill"):
        print_format = frappe.get_doc("Print Format", "Waybill")
        print_format.html = html_content
        print_format.save()
        print("✓ Updated existing Waybill print format")
    else:
        # Create new print format
        print_format = frappe.get_doc({
            "doctype": "Print Format",
            "name": "Waybill",
            "doc_type": "Transport Leg",
            "module": "Transport",
            "standard": "No",
            "custom_format": 1,
            "print_format_type": "Jinja",
            "html": html_content,
            "font_size": 9,
            "disabled": 0,
            "align_labels_right": 0,
            "line_breaks": 0,
            "print_format_builder": 0,
            "raw_printing": 0,
            "show_section_headings": 0
        })
        print_format.insert(ignore_permissions=True)
        print("✓ Created new Waybill print format")
    
    frappe.db.commit()
    print("✓ Waybill print format installed successfully!")
    print("  You can now use it from Transport Leg > Print > Waybill")

if __name__ == "__main__":
    import sys
    site = sys.argv[1] if len(sys.argv) > 1 else None
    if site:
        frappe.init(site=site)
        frappe.connect()
        install_waybill_print_format()
    else:
        print("Please provide a site name as argument")

