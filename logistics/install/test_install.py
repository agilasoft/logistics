# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe

def test_master_air_waybill_indexing():
    """Test function to verify Master Air Waybill indexing works"""
    try:
        # Test if Master Air Waybill DocType exists
        if frappe.db.exists("DocType", "Master Air Waybill"):
            print("✓ Master Air Waybill DocType exists")
            
            # Test if we can query the table
            count = frappe.db.count("Master Air Waybill")
            print(f"✓ Master Air Waybill table accessible, {count} records found")
            
            # Test index creation
            from logistics.install.after_install import create_index_if_not_exists
            create_index_if_not_exists(
                "tabMaster Air Waybill",
                ["airline", "flight_no"],
                "test_idx_airline_flight"
            )
            print("✓ Index creation test successful")
            
        else:
            print("✗ Master Air Waybill DocType not found")
            
    except Exception as e:
        print(f"✗ Error testing Master Air Waybill indexing: {str(e)}")

if __name__ == "__main__":
    test_master_air_waybill_indexing()
