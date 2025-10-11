"""
Test script for dimensions implementation in order items and allocation items.
"""

import frappe
from frappe import _


def test_dimensions_fields():
    """Test that dimension fields are properly added to order and allocation items."""
    print("Testing Dimensions Fields Implementation...")
    
    # Test 1: Check Inbound Order Item fields
    try:
        fields = frappe.get_meta("Inbound Order Item").fields
        field_names = [f.fieldname for f in fields]
        
        required_fields = ['length', 'width', 'height', 'volume', 'weight', 'dimensions_section']
        for field in required_fields:
            if field in field_names:
                print(f"✓ {field} field exists in Inbound Order Item")
            else:
                print(f"✗ {field} field missing in Inbound Order Item")
                
    except Exception as e:
        print(f"✗ Error checking Inbound Order Item fields: {e}")
    
    # Test 2: Check VAS Order Item fields
    try:
        fields = frappe.get_meta("VAS Order Item").fields
        field_names = [f.fieldname for f in fields]
        
        required_fields = ['length', 'width', 'height', 'volume', 'weight', 'dimensions_section']
        for field in required_fields:
            if field in field_names:
                print(f"✓ {field} field exists in VAS Order Item")
            else:
                print(f"✗ {field} field missing in VAS Order Item")
                
    except Exception as e:
        print(f"✗ Error checking VAS Order Item fields: {e}")
    
    # Test 3: Check Warehouse Job Order Items fields
    try:
        fields = frappe.get_meta("Warehouse Job Order Items").fields
        field_names = [f.fieldname for f in fields]
        
        required_fields = ['length', 'width', 'height', 'volume', 'weight', 'dimensions_section']
        for field in required_fields:
            if field in field_names:
                print(f"✓ {field} field exists in Warehouse Job Order Items")
            else:
                print(f"✗ {field} field missing in Warehouse Job Order Items")
                
    except Exception as e:
        print(f"✗ Error checking Warehouse Job Order Items fields: {e}")
    
    # Test 4: Check Warehouse Job Item fields (allocation items)
    try:
        fields = frappe.get_meta("Warehouse Job Item").fields
        field_names = [f.fieldname for f in fields]
        
        required_fields = ['length', 'width', 'height', 'volume', 'weight', 'dimensions_section']
        for field in required_fields:
            if field in field_names:
                print(f"✓ {field} field exists in Warehouse Job Item")
            else:
                print(f"✗ {field} field missing in Warehouse Job Item")
                
    except Exception as e:
        print(f"✗ Error checking Warehouse Job Item fields: {e}")
    
    # Test 5: Check Warehouse Item fields
    try:
        fields = frappe.get_meta("Warehouse Item").fields
        field_names = [f.fieldname for f in fields]
        
        required_fields = ['length', 'width', 'height', 'volume', 'weight', 'dimensions_tab']
        for field in required_fields:
            if field in field_names:
                print(f"✓ {field} field exists in Warehouse Item")
            else:
                print(f"✗ {field} field missing in Warehouse Item")
                
    except Exception as e:
        print(f"✗ Error checking Warehouse Item fields: {e}")
    
    print("\nDimensions Fields Test Complete!")


def test_volume_calculation_functions():
    """Test volume calculation functions with item dimensions."""
    print("\nTesting Volume Calculation Functions...")
    
    try:
        from logistics.warehousing.api_parts.volume_billing import (
            _get_item_volume_from_ledger,
            calculate_volume_usage
        )
        print("✓ Volume calculation functions imported successfully")
        
        # Test function signatures
        import inspect
        
        # Check _get_item_volume_from_ledger signature
        sig = inspect.signature(_get_item_volume_from_ledger)
        expected_params = ['handling_unit', 'check_date']
        for param in expected_params:
            if param in sig.parameters:
                print(f"✓ _get_item_volume_from_ledger has {param} parameter")
            else:
                print(f"✗ _get_item_volume_from_ledger missing {param} parameter")
        
        # Check calculate_volume_usage signature
        sig = inspect.signature(calculate_volume_usage)
        expected_params = ['handling_unit', 'date_from', 'date_to', 'calculation_method']
        for param in expected_params:
            if param in sig.parameters:
                print(f"✓ calculate_volume_usage has {param} parameter")
            else:
                print(f"✗ calculate_volume_usage missing {param} parameter")
                
    except Exception as e:
        print(f"✗ Error testing volume calculation functions: {e}")
    
    print("\nVolume Calculation Functions Test Complete!")


def test_javascript_files():
    """Test that JavaScript files exist for automatic volume calculation."""
    print("\nTesting JavaScript Files...")
    
    js_files = [
        "logistics/warehousing/doctype/inbound_order_item/inbound_order_item.js",
        "logistics/warehousing/doctype/vas_order_item/vas_order_item.js",
        "logistics/warehousing/doctype/warehouse_job_order_items/warehouse_job_order_items.js",
        "logistics/warehousing/doctype/warehouse_job_item/warehouse_job_item.js",
        "logistics/warehousing/doctype/warehouse_item/warehouse_item.js"
    ]
    
    for js_file in js_files:
        try:
            with open(js_file, 'r') as f:
                content = f.read()
                if 'calculate_volume' in content:
                    print(f"✓ {js_file} contains volume calculation logic")
                else:
                    print(f"✗ {js_file} missing volume calculation logic")
        except FileNotFoundError:
            print(f"✗ {js_file} file not found")
        except Exception as e:
            print(f"✗ Error reading {js_file}: {e}")
    
    print("\nJavaScript Files Test Complete!")


def test_field_precision():
    """Test that dimension fields have proper precision settings."""
    print("\nTesting Field Precision Settings...")
    
    doctypes_to_check = [
        "Inbound Order Item",
        "VAS Order Item", 
        "Warehouse Job Order Items",
        "Warehouse Job Item",
        "Warehouse Item"
    ]
    
    for doctype in doctypes_to_check:
        try:
            fields = frappe.get_meta(doctype).fields
            dimension_fields = ['length', 'width', 'height', 'volume', 'weight']
            
            for field in fields:
                if field.fieldname in dimension_fields:
                    if hasattr(field, 'precision') and field.precision == 3:
                        print(f"✓ {doctype}.{field.fieldname} has precision 3")
                    else:
                        print(f"✗ {doctype}.{field.fieldname} missing or incorrect precision")
                        
        except Exception as e:
            print(f"✗ Error checking {doctype} field precision: {e}")
    
    print("\nField Precision Test Complete!")


if __name__ == "__main__":
    print("=" * 60)
    print("DIMENSIONS IMPLEMENTATION TEST")
    print("=" * 60)
    
    test_dimensions_fields()
    test_volume_calculation_functions()
    test_javascript_files()
    test_field_precision()
    
    print("\n" + "=" * 60)
    print("ALL DIMENSIONS TESTS COMPLETED")
    print("=" * 60)

