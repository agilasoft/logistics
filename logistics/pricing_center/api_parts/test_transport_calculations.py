# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""
Test script for Transport Rate Calculation Engine

This script tests the calculation logic with sample data to ensure
all calculation methods work correctly.
"""

import frappe
from frappe import _
from frappe.utils import flt
import json

from logistics.pricing_center.api_parts.transport_rate_calculation_engine import (
    TransportRateCalculationEngine,
    calculate_transport_rate_for_quote,
    get_transport_rates_for_route,
    validate_rate_data
)


def test_transport_calculation_engine():
    """
    Test the Transport Rate Calculation Engine with various scenarios
    """
    
    print("=" * 60)
    print("TESTING TRANSPORT RATE CALCULATION ENGINE")
    print("=" * 60)
    
    # Initialize calculator
    calculator = TransportRateCalculationEngine()
    
    # Test scenarios
    test_scenarios = [
        {
            'name': 'Per Unit - Weight Based',
            'rate_data': {
                'calculation_method': 'Per Unit',
                'rate': 10.50,
                'unit_type': 'Weight',
                'currency': 'USD',
                'item_code': 'TRANS-001',
                'item_name': 'Transport Service'
            },
            'actual_data': {
                'actual_weight': 100,  # 100 kg
                'actual_quantity': 100
            },
            'expected_amount': 1050.00  # 10.50 * 100
        },
        {
            'name': 'Per Unit - Distance Based',
            'rate_data': {
                'calculation_method': 'Per Unit',
                'rate': 2.50,
                'unit_type': 'Distance',
                'currency': 'USD',
                'item_code': 'TRANS-002',
                'item_name': 'Distance Transport'
            },
            'actual_data': {
                'actual_distance': 50,  # 50 km
            },
            'expected_amount': 125.00  # 2.50 * 50
        },
        {
            'name': 'Fixed Amount',
            'rate_data': {
                'calculation_method': 'Fixed Amount',
                'fixed_amount': 500.00,
                'currency': 'USD',
                'item_code': 'TRANS-003',
                'item_name': 'Fixed Transport'
            },
            'actual_data': {
                'actual_weight': 100
            },
            'expected_amount': 500.00
        },
        {
            'name': 'Flat Rate',
            'rate_data': {
                'calculation_method': 'Flat Rate',
                'rate': 300.00,
                'currency': 'USD',
                'item_code': 'TRANS-004',
                'item_name': 'Flat Rate Transport'
            },
            'actual_data': {
                'actual_weight': 100
            },
            'expected_amount': 300.00
        },
        {
            'name': 'Base Plus Additional',
            'rate_data': {
                'calculation_method': 'Base Plus Additional',
                'base_amount': 200.00,
                'rate': 5.00,
                'unit_type': 'Weight',
                'currency': 'USD',
                'item_code': 'TRANS-005',
                'item_name': 'Base Plus Transport'
            },
            'actual_data': {
                'actual_weight': 50  # 50 kg
            },
            'expected_amount': 450.00  # 200 + (5 * 50)
        },
        {
            'name': 'First Plus Additional',
            'rate_data': {
                'calculation_method': 'First Plus Additional',
                'rate': 100.00,
                'minimum_quantity': 10,
                'unit_type': 'Weight',
                'currency': 'USD',
                'item_code': 'TRANS-006',
                'item_name': 'First Plus Transport'
            },
            'actual_data': {
                'actual_weight': 25  # 25 kg (10 + 15 additional)
            },
            'expected_amount': 175.00  # 100 + (100 * 0.5 * 15)
        },
        {
            'name': 'Percentage',
            'rate_data': {
                'calculation_method': 'Percentage',
                'base_amount': 1000.00,
                'rate': 15,  # 15%
                'currency': 'USD',
                'item_code': 'TRANS-007',
                'item_name': 'Percentage Transport'
            },
            'actual_data': {
                'actual_weight': 100
            },
            'expected_amount': 150.00  # 1000 * 0.15
        },
        {
            'name': 'Minimum Charge Applied',
            'rate_data': {
                'calculation_method': 'Per Unit',
                'rate': 2.00,
                'unit_type': 'Weight',
                'minimum_charge': 500.00,
                'currency': 'USD',
                'item_code': 'TRANS-008',
                'item_name': 'Min Charge Transport'
            },
            'actual_data': {
                'actual_weight': 100  # 2 * 100 = 200, but min is 500
            },
            'expected_amount': 500.00
        },
        {
            'name': 'Maximum Charge Applied',
            'rate_data': {
                'calculation_method': 'Per Unit',
                'rate': 10.00,
                'unit_type': 'Weight',
                'maximum_charge': 800.00,
                'currency': 'USD',
                'item_code': 'TRANS-009',
                'item_name': 'Max Charge Transport'
            },
            'actual_data': {
                'actual_weight': 100  # 10 * 100 = 1000, but max is 800
            },
            'expected_amount': 800.00
        }
    ]
    
    # Run tests
    passed_tests = 0
    failed_tests = 0
    
    for scenario in test_scenarios:
        print(f"\nTesting: {scenario['name']}")
        print("-" * 40)
        
        try:
            # Calculate rate
            result = calculator.calculate_transport_rate(
                rate_data=scenario['rate_data'],
                **scenario['actual_data']
            )
            
            if result.get('success'):
                calculated_amount = result.get('amount', 0)
                expected_amount = scenario['expected_amount']
                
                print(f"Expected: {expected_amount}")
                print(f"Calculated: {calculated_amount}")
                print(f"Rate Data: {scenario['rate_data']}")
                print(f"Actual Data: {scenario['actual_data']}")
                
                # Check if amounts match (with small tolerance for floating point)
                if abs(calculated_amount - expected_amount) < 0.01:
                    print("✅ PASSED")
                    passed_tests += 1
                else:
                    print("❌ FAILED - Amount mismatch")
                    failed_tests += 1
            else:
                print(f"❌ FAILED - Calculation error: {result.get('error')}")
                failed_tests += 1
                
        except Exception as e:
            print(f"❌ FAILED - Exception: {str(e)}")
            failed_tests += 1
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {len(test_scenarios)}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {(passed_tests / len(test_scenarios)) * 100:.1f}%")
    
    return {
        'total_tests': len(test_scenarios),
        'passed': passed_tests,
        'failed': failed_tests,
        'success_rate': (passed_tests / len(test_scenarios)) * 100
    }


def test_api_functions():
    """
    Test the API functions
    """
    
    print("\n" + "=" * 60)
    print("TESTING API FUNCTIONS")
    print("=" * 60)
    
    # Test rate data validation
    print("\nTesting rate data validation...")
    
    valid_rate_data = {
        'calculation_method': 'Per Unit',
        'rate': 10.00,
        'currency': 'USD',
        'item_code': 'TEST-001'
    }
    
    validation_result = validate_rate_data(valid_rate_data)
    print(f"Valid rate data validation: {validation_result}")
    
    # Test invalid rate data
    invalid_rate_data = {
        'calculation_method': 'Per Unit',
        # Missing rate
        'currency': 'USD'
    }
    
    validation_result = validate_rate_data(invalid_rate_data)
    print(f"Invalid rate data validation: {validation_result}")
    
    print("\nAPI function tests completed.")


def test_sales_quote_integration():
    """
    Test Sales Quote integration functions
    """
    
    print("\n" + "=" * 60)
    print("TESTING SALES QUOTE INTEGRATION")
    print("=" * 60)
    
    try:
        # Test rate calculation for quote
        rate_data = {
            'calculation_method': 'Per Unit',
            'rate': 15.00,
            'unit_type': 'Weight',
            'currency': 'USD',
            'item_code': 'SQ-TEST-001',
            'item_name': 'Sales Quote Test Transport'
        }
        
        actual_data = {
            'actual_weight': 75
        }
        
        print("Testing calculate_transport_rate_for_quote...")
        result = calculate_transport_rate_for_quote(
            rate_data=json.dumps(rate_data),
            **actual_data
        )
        
        print(f"Result: {result}")
        
        if result.get('success'):
            print("✅ Sales Quote integration test PASSED")
        else:
            print(f"❌ Sales Quote integration test FAILED: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Sales Quote integration test FAILED with exception: {str(e)}")


def run_all_tests():
    """
    Run all tests
    """
    
    print("STARTING TRANSPORT RATE CALCULATION TESTS")
    print("=" * 60)
    
    # Test calculation engine
    engine_results = test_transport_calculation_engine()
    
    # Test API functions
    test_api_functions()
    
    # Test Sales Quote integration
    test_sales_quote_integration()
    
    # Final summary
    print("\n" + "=" * 60)
    print("FINAL TEST SUMMARY")
    print("=" * 60)
    print(f"Calculation Engine Tests: {engine_results['passed']}/{engine_results['total_tests']} passed")
    print(f"Success Rate: {engine_results['success_rate']:.1f}%")
    
    if engine_results['success_rate'] >= 90:
        print("🎉 All tests completed successfully!")
    else:
        print("⚠️  Some tests failed. Please review the results above.")
    
    return engine_results


# Main execution
if __name__ == "__main__":
    run_all_tests()


