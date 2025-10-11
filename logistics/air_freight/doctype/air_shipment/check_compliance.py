#!/usr/bin/env python3
"""
Check DG compliance for AF000000001
"""

import frappe

def check_af_compliance():
    """Check compliance for AF000000001"""
    
    print("Checking AF000000001 compliance...")
    
    try:
        # Get the job
        job = frappe.get_doc('Air Freight Job', 'AF000000001')
        
        print(f"Job Name: {job.name}")
        print(f"Contains DG: {getattr(job, 'contains_dangerous_goods', False)}")
        print(f"DG Emergency Contact: {getattr(job, 'dg_emergency_contact', None)}")
        print(f"DG Emergency Phone: {getattr(job, 'dg_emergency_phone', None)}")
        print(f"DG Declaration Complete: {getattr(job, 'dg_declaration_complete', False)}")
        print(f"DG Compliance Status: {getattr(job, 'dg_compliance_status', None)}")
        print(f"Packages Count: {len(job.packages) if job.packages else 0}")
        
        # Check compliance
        print("\n=== COMPLIANCE CHECK ===")
        result = job.check_dg_compliance()
        print(f"Status: {result.get('status')}")
        print(f"Message: {result.get('message')}")
        if result.get('issues'):
            print(f"Issues: {result.get('issues')}")
        
        # Check DG dashboard info
        print("\n=== DG DASHBOARD INFO ===")
        dg_info = job.get_dg_dashboard_info()
        print(f"Has DG: {dg_info.get('has_dg')}")
        print(f"Alert Level: {dg_info.get('alert_level')}")
        print(f"Message: {dg_info.get('message')}")
        print(f"Compliance Status: {dg_info.get('compliance_status')}")
        print(f"DG Packages: {dg_info.get('dg_packages')}")
        print(f"Compliance Issues: {dg_info.get('compliance_issues')}")
        
        # Check packages
        print("\n=== PACKAGES ===")
        for i, package in enumerate(job.packages):
            print(f"Package {i+1}:")
            print(f"  Commodity: {package.commodity}")
            print(f"  DG Substance: {package.dg_substance}")
            print(f"  UN Number: {package.un_number}")
            print(f"  Proper Shipping Name: {package.proper_shipping_name}")
            print(f"  DG Class: {package.dg_class}")
            print(f"  Packing Group: {package.packing_group}")
            print(f"  Emergency Contact Name: {package.emergency_contact_name}")
            print(f"  Emergency Contact Phone: {package.emergency_contact_phone}")
            print()
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_af_compliance()
