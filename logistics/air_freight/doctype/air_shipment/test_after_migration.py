#!/usr/bin/env python3
"""
Test dangerous goods functionality after migration
"""

import frappe

def test_dg_after_migration():
    """Test dangerous goods functionality after migration"""
    
    print("Testing dangerous goods functionality after migration...")
    
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
        has_fields = job.has_dg_fields()
        print(f"✅ has_dg_fields(): {has_fields}")
        
        # Test get_dg_dashboard_info method
        try:
            dg_info = job.get_dg_dashboard_info()
            print(f"✅ get_dg_dashboard_info(): {dg_info}")
        except Exception as e:
            print(f"❌ get_dg_dashboard_info() failed: {str(e)}")
        
        # Test check_dg_compliance method
        try:
            compliance = job.check_dg_compliance()
            print(f"✅ check_dg_compliance(): {compliance}")
        except Exception as e:
            print(f"❌ check_dg_compliance() failed: {str(e)}")
        
        # Test send_dg_alert method
        try:
            alert = job.send_dg_alert("compliance")
            print(f"✅ send_dg_alert(): {alert}")
        except Exception as e:
            print(f"❌ send_dg_alert() failed: {str(e)}")
        
        print("\n🎉 Dangerous goods functionality test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_dg_after_migration()
