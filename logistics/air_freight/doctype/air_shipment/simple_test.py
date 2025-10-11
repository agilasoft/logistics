#!/usr/bin/env python3
"""
Simple test for dangerous goods functionality
"""

import frappe

def test_dg_methods():
    """Test dangerous goods methods"""
    
    print("Testing dangerous goods functionality...")
    
    try:
        # Get an existing Air Freight Job
        jobs = frappe.get_all("Air Freight Job", limit=1)
        if not jobs:
            print("❌ No Air Freight Jobs found")
            return
        
        job_name = jobs[0].name
        print(f"Testing with Air Freight Job: {job_name}")
        
        # Get the job document
        job = frappe.get_doc("Air Freight Job", job_name)
        
        # Test has_dg_fields method
        print(f"✅ has_dg_fields(): {job.has_dg_fields()}")
        
        # Test get_dg_dashboard_info method
        try:
            dg_info = job.get_dg_dashboard_info()
            print(f"✅ get_dg_dashboard_info(): {dg_info}")
        except Exception as e:
            print(f"❌ get_dg_dashboard_info() failed: {str(e)}")
        
        print("\n🎉 Test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_dg_methods()
