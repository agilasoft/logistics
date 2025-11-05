#!/usr/bin/env python3
"""
Install all default print formats for Logistics module
Run with: bench --site <site_name> execute logistics.print_format.install_now.install_all_print_formats
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


