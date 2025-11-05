#!/usr/bin/env python3
"""
Install all default print formats for Logistics module
"""
import frappe
from logistics.print_format.sales_invoice.install_print_format import install_sales_invoice_print_format
from logistics.print_format.purchase_invoice.install_print_format import install_purchase_invoice_print_format

def install_all_print_formats():
    """Install all default print formats"""
    print("Installing default print formats...")
    
    try:
        # Install Sales Invoice print format
        install_sales_invoice_print_format()
        
        # Install Purchase Invoice print format
        install_purchase_invoice_print_format()
        
        print("\n✅ All print formats installed successfully!")
        
    except Exception as e:
        print(f"❌ Error installing print formats: {e}")
        frappe.log_error(f"Print format installation error: {str(e)}")
        raise

if __name__ == "__main__":
    import sys
    site = sys.argv[1] if len(sys.argv) > 1 else None
    if site:
        frappe.init(site=site)
        frappe.connect()
        install_all_print_formats()
    else:
        print("Please provide a site name as argument")


