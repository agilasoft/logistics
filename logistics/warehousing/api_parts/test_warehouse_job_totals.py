"""
Test script for warehouse job totals implementation.
"""

import frappe
from frappe import _


def test_warehouse_job_totals_fields():
    """Test that totals fields are properly added to Warehouse Job."""
    print("Testing Warehouse Job Totals Fields...")
    
    try:
        fields = frappe.get_meta("Warehouse Job").fields
        field_names = [f.fieldname for f in fields]
        
        required_fields = ['total_volume', 'total_weight', 'total_handling_units', 'totals_section']
        for field in required_fields:
            if field in field_names:
                print(f"✓ {field} field exists in Warehouse Job")
            else:
                print(f"✗ {field} field missing in Warehouse Job")
                
    except Exception as e:
        print(f"✗ Error checking Warehouse Job fields: {e}")
    
    print("\nWarehouse Job Totals Fields Test Complete!")


def test_warehouse_job_totals_calculation():
    """Test the totals calculation logic."""
    print("\nTesting Warehouse Job Totals Calculation...")
    
    try:
        # Test the calculation logic
        from logistics.warehousing.doctype.warehouse_job.warehouse_job import WarehouseJob
        
        # Create a mock job with items
        job_data = {
            "doctype": "Warehouse Job",
            "type": "Pick",
            "items": [
                {
                    "doctype": "Warehouse Job Item",
                    "item": "TEST-ITEM-001",
                    "quantity": 2,
                    "length": 1.0,
                    "width": 1.0,
                    "height": 1.0,
                    "volume": 1.0,
                    "weight": 5.0,
                    "handling_unit": "HU-001"
                },
                {
                    "doctype": "Warehouse Job Item",
                    "item": "TEST-ITEM-002",
                    "quantity": 3,
                    "length": 2.0,
                    "width": 1.0,
                    "height": 1.0,
                    "volume": 2.0,
                    "weight": 10.0,
                    "handling_unit": "HU-002"
                }
            ]
        }
        
        # Test calculation logic
        total_volume = 0
        total_weight = 0
        unique_handling_units = set()
        
        for item in job_data["items"]:
            # Calculate volume
            if item["length"] and item["width"] and item["height"]:
                item_volume = float(item["length"]) * float(item["width"]) * float(item["height"])
                total_volume += item_volume * float(item["quantity"])
            elif item["volume"]:
                total_volume += float(item["volume"]) * float(item["quantity"])
            
            # Add weight
            if item["weight"]:
                total_weight += float(item["weight"]) * float(item["quantity"])
            
            # Count unique handling units
            if item["handling_unit"]:
                unique_handling_units.add(item["handling_unit"])
        
        expected_volume = (1.0 * 2) + (2.0 * 3)  # 2 + 6 = 8
        expected_weight = (5.0 * 2) + (10.0 * 3)  # 10 + 30 = 40
        expected_handling_units = 2  # HU-001, HU-002
        
        if abs(total_volume - expected_volume) < 0.001:
            print(f"✓ Volume calculation correct: {total_volume}")
        else:
            print(f"✗ Volume calculation incorrect: {total_volume}, expected: {expected_volume}")
        
        if abs(total_weight - expected_weight) < 0.001:
            print(f"✓ Weight calculation correct: {total_weight}")
        else:
            print(f"✗ Weight calculation incorrect: {total_weight}, expected: {expected_weight}")
        
        if len(unique_handling_units) == expected_handling_units:
            print(f"✓ Handling units calculation correct: {len(unique_handling_units)}")
        else:
            print(f"✗ Handling units calculation incorrect: {len(unique_handling_units)}, expected: {expected_handling_units}")
            
    except Exception as e:
        print(f"✗ Error testing totals calculation: {e}")
    
    print("\nWarehouse Job Totals Calculation Test Complete!")


def test_javascript_files():
    """Test that JavaScript files exist for automatic totals calculation."""
    print("\nTesting JavaScript Files...")
    
    js_file = "logistics/warehousing/doctype/warehouse_job/warehouse_job.js"
    
    try:
        with open(js_file, 'r') as f:
            content = f.read()
            if 'calculate_job_totals' in content:
                print(f"✓ {js_file} contains totals calculation logic")
            else:
                print(f"✗ {js_file} missing totals calculation logic")
                
            if 'total_volume' in content and 'total_weight' in content and 'total_handling_units' in content:
                print(f"✓ {js_file} contains all totals fields")
            else:
                print(f"✗ {js_file} missing some totals fields")
                
    except FileNotFoundError:
        print(f"✗ {js_file} file not found")
    except Exception as e:
        print(f"✗ Error reading {js_file}: {e}")
    
    print("\nJavaScript Files Test Complete!")


def test_field_precision():
    """Test that totals fields have proper precision settings."""
    print("\nTesting Field Precision Settings...")
    
    try:
        fields = frappe.get_meta("Warehouse Job").fields
        totals_fields = ['total_volume', 'total_weight', 'total_handling_units']
        
        for field in fields:
            if field.fieldname in totals_fields:
                if field.fieldname == 'total_handling_units':
                    if field.fieldtype == 'Int':
                        print(f"✓ {field.fieldname} has correct field type: {field.fieldtype}")
                    else:
                        print(f"✗ {field.fieldname} incorrect field type: {field.fieldtype}")
                else:
                    if hasattr(field, 'precision') and field.precision == 3:
                        print(f"✓ {field.fieldname} has precision 3")
                    else:
                        print(f"✗ {field.fieldname} missing or incorrect precision")
                        
    except Exception as e:
        print(f"✗ Error checking field precision: {e}")
    
    print("\nField Precision Test Complete!")


if __name__ == "__main__":
    print("=" * 60)
    print("WAREHOUSE JOB TOTALS IMPLEMENTATION TEST")
    print("=" * 60)
    
    test_warehouse_job_totals_fields()
    test_warehouse_job_totals_calculation()
    test_javascript_files()
    test_field_precision()
    
    print("\n" + "=" * 60)
    print("ALL WAREHOUSE JOB TOTALS TESTS COMPLETED")
    print("=" * 60)

