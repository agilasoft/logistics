#!/usr/bin/env python3

import frappe
from frappe import _

def debug_periodic_billing():
    """Debug the periodic billing get charges function"""
    try:
        # Initialize Frappe
        frappe.init(site='localhost')
        frappe.connect()
        
        # Test the function
        print("Testing periodic_billing_get_charges...")
        
        # First, let's see if we can get a periodic billing document
        pb_docs = frappe.get_all("Periodic Billing", limit=1)
        if not pb_docs:
            print("No Periodic Billing documents found")
            return
            
        pb_name = pb_docs[0].name
        print(f"Testing with Periodic Billing: {pb_name}")
        
        # Get the document
        pb = frappe.get_doc("Periodic Billing", pb_name)
        print(f"Customer: {pb.customer}")
        print(f"Date From: {pb.date_from}")
        print(f"Date To: {pb.date_to}")
        print(f"Warehouse Contract: {pb.warehouse_contract}")
        
        # Test the function
        result = frappe.call('logistics.warehousing.billing.periodic_billing_get_charges', 
                           periodic_billing=pb_name, 
                           clear_existing=1)
        print("Result:", result)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_periodic_billing()
