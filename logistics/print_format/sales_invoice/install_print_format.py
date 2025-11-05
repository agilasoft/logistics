#!/usr/bin/env python3
"""
Install BIR Sales Invoice Print Format
"""
import frappe
import os

def install_sales_invoice_print_format():
    """Install or update the BIR Sales Invoice print format"""
    
    # Get the HTML content
    html_path = os.path.join(os.path.dirname(__file__), 'sales_invoice.html')
    
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Check if print format exists
    if frappe.db.exists("Print Format", "BIR Sales Invoice"):
        print_format = frappe.get_doc("Print Format", "BIR Sales Invoice")
        print_format.html = html_content
        print_format.save()
        print("✓ Updated existing BIR Sales Invoice print format")
    else:
        # Create new print format
        print_format = frappe.get_doc({
            "doctype": "Print Format",
            "name": "BIR Sales Invoice",
            "doc_type": "Sales Invoice",
            "module": "Logistics",
            "standard": "No",
            "custom_format": 1,
            "print_format_type": "Jinja",
            "html": html_content,
            "font_size": 8,
            "disabled": 0,
            "align_labels_right": 0,
            "line_breaks": 0,
            "print_format_builder": 0,
            "raw_printing": 0,
            "show_section_headings": 0
        })
        print_format.insert(ignore_permissions=True)
        print("✓ Created new BIR Sales Invoice print format")
    
    frappe.db.commit()
    print("✓ BIR Sales Invoice print format installed successfully!")
    print("  You can now use it from Sales Invoice > Print > BIR Sales Invoice")

if __name__ == "__main__":
    import sys
    site = sys.argv[1] if len(sys.argv) > 1 else None
    if site:
        frappe.init(site=site)
        frappe.connect()
        install_sales_invoice_print_format()
    else:
        print("Please provide a site name as argument")


