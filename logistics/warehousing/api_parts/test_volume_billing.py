"""
Test script for volume-based billing functionality.
"""

import frappe
from frappe import _


def test_volume_billing_setup():
    """Test that volume billing settings are properly configured."""
    print("Testing Volume Billing Setup...")
    
    # Test 1: Check if Warehouse Settings has volume billing fields
    try:
        company = frappe.defaults.get_user_default("Company")
        settings = frappe.get_doc("Warehouse Settings", company)
        print("✓ Warehouse Settings loaded successfully")
        
        # Check if new fields exist
        if hasattr(settings, 'enable_volume_billing'):
            print("✓ enable_volume_billing field exists")
        else:
            print("✗ enable_volume_billing field missing")
            
        if hasattr(settings, 'default_volume_uom'):
            print("✓ default_volume_uom field exists")
        else:
            print("✗ default_volume_uom field missing")
            
    except Exception as e:
        print(f"✗ Error loading Warehouse Settings: {e}")
    
    # Test 2: Check if Warehouse Contract Item has volume billing fields
    try:
        contract_item_fields = frappe.get_meta("Warehouse Contract Item").fields
        field_names = [f.fieldname for f in contract_item_fields]
        
        required_fields = ['billing_method', 'volume_uom', 'volume_calculation_method']
        for field in required_fields:
            if field in field_names:
                print(f"✓ {field} field exists in Warehouse Contract Item")
            else:
                print(f"✗ {field} field missing in Warehouse Contract Item")
                
    except Exception as e:
        print(f"✗ Error checking Warehouse Contract Item fields: {e}")
    
    # Test 3: Check if charges tables have volume billing fields
    charges_tables = ["Warehouse Job Charges", "Periodic Billing Charges"]
    for table in charges_tables:
        try:
            fields = frappe.get_meta(table).fields
            field_names = [f.fieldname for f in fields]
            
            required_fields = ['billing_method', 'volume_quantity', 'volume_uom']
            for field in required_fields:
                if field in field_names:
                    print(f"✓ {field} field exists in {table}")
                else:
                    print(f"✗ {field} field missing in {table}")
                    
        except Exception as e:
            print(f"✗ Error checking {table} fields: {e}")
    
    print("\nVolume Billing Setup Test Complete!")


def test_volume_calculation_functions():
    """Test volume calculation functions."""
    print("\nTesting Volume Calculation Functions...")
    
    try:
        from logistics.warehousing.api_parts.volume_billing import (
            calculate_volume_usage,
            create_volume_based_charge_line,
            get_volume_billing_quantity
        )
        print("✓ Volume billing functions imported successfully")
        
        # Test function signatures
        import inspect
        
        # Check calculate_volume_usage signature
        sig = inspect.signature(calculate_volume_usage)
        expected_params = ['handling_unit', 'date_from', 'date_to', 'calculation_method']
        for param in expected_params:
            if param in sig.parameters:
                print(f"✓ calculate_volume_usage has {param} parameter")
            else:
                print(f"✗ calculate_volume_usage missing {param} parameter")
        
        # Check create_volume_based_charge_line signature
        sig = inspect.signature(create_volume_based_charge_line)
        expected_params = ['handling_unit', 'date_from', 'date_to', 'contract_item', 'storage_location']
        for param in expected_params:
            if param in sig.parameters:
                print(f"✓ create_volume_based_charge_line has {param} parameter")
            else:
                print(f"✗ create_volume_based_charge_line missing {param} parameter")
                
    except Exception as e:
        print(f"✗ Error testing volume calculation functions: {e}")
    
    print("\nVolume Calculation Functions Test Complete!")


def test_periodic_billing_integration():
    """Test periodic billing integration."""
    print("\nTesting Periodic Billing Integration...")
    
    try:
        from logistics.warehousing.api import periodic_billing_get_volume_charges
        print("✓ periodic_billing_get_volume_charges function imported successfully")
        
        # Check function signature
        import inspect
        sig = inspect.signature(periodic_billing_get_volume_charges)
        expected_params = ['periodic_billing', 'clear_existing']
        for param in expected_params:
            if param in sig.parameters:
                print(f"✓ periodic_billing_get_volume_charges has {param} parameter")
            else:
                print(f"✗ periodic_billing_get_volume_charges missing {param} parameter")
                
    except Exception as e:
        print(f"✗ Error testing periodic billing integration: {e}")
    
    print("\nPeriodic Billing Integration Test Complete!")


if __name__ == "__main__":
    print("=" * 50)
    print("VOLUME-BASED BILLING IMPLEMENTATION TEST")
    print("=" * 50)
    
    test_volume_billing_setup()
    test_volume_calculation_functions()
    test_periodic_billing_integration()
    
    print("\n" + "=" * 50)
    print("ALL TESTS COMPLETED")
    print("=" * 50)

