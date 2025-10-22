# -*- coding: utf-8 -*-
"""
Test script to verify storage location status update mechanism.
"""

import frappe
from frappe import _


@frappe.whitelist()
def test_status_update_mechanism() -> dict:
    """
    Test the storage location status update mechanism.
    """
    try:
        results = {
            "test_results": [],
            "summary": {}
        }
        
        # Test 1: Check if _set_sl_status_by_balance function exists and works
        test1_result = _test_status_update_function()
        results["test_results"].append(test1_result)
        
        # Test 2: Check if status field exists on Storage Location
        test2_result = _test_status_field_exists()
        results["test_results"].append(test2_result)
        
        # Test 3: Check balance calculation logic
        test3_result = _test_balance_calculation()
        results["test_results"].append(test3_result)
        
        # Test 4: Check if status updates are called in key functions
        test4_result = _test_status_update_triggers()
        results["test_results"].append(test4_result)
        
        # Generate summary
        results["summary"] = _generate_test_summary(results["test_results"])
        
        return results
        
    except Exception as e:
        frappe.log_error(f"Error in test_status_update_mechanism: {str(e)}")
        return {"error": str(e)}


def _test_status_update_function() -> dict:
    """Test if _set_sl_status_by_balance function exists and works."""
    try:
        from logistics.warehousing.api import _set_sl_status_by_balance, _sl_balance, _sl_fields
        
        # Check if function exists
        if not callable(_set_sl_status_by_balance):
            return {"test": "status_update_function", "status": "FAIL", "message": "Function _set_sl_status_by_balance not found"}
        
        # Check if _sl_fields returns status field
        sl_fields = _sl_fields()
        has_status_field = "status" in sl_fields
        
        if not has_status_field:
            return {"test": "status_update_function", "status": "FAIL", "message": "Storage Location doctype doesn't have 'status' field"}
        
        return {"test": "status_update_function", "status": "PASS", "message": "Function exists and status field is available"}
        
    except Exception as e:
        return {"test": "status_update_function", "status": "ERROR", "message": str(e)}


def _test_status_field_exists() -> dict:
    """Test if status field exists on Storage Location doctype."""
    try:
        from logistics.warehousing.api import _sl_fields
        
        sl_fields = _sl_fields()
        has_status_field = "status" in sl_fields
        
        if has_status_field:
            return {"test": "status_field_exists", "status": "PASS", "message": "Status field exists on Storage Location"}
        else:
            return {"test": "status_field_exists", "status": "FAIL", "message": "Status field missing from Storage Location doctype"}
            
    except Exception as e:
        return {"test": "status_field_exists", "status": "ERROR", "message": str(e)}


def _test_balance_calculation() -> dict:
    """Test balance calculation logic."""
    try:
        from logistics.warehousing.api import _sl_balance
        
        # Test with a non-existent location
        balance = _sl_balance("NON_EXISTENT_LOCATION")
        if balance == 0.0:
            return {"test": "balance_calculation", "status": "PASS", "message": "Balance calculation works correctly"}
        else:
            return {"test": "balance_calculation", "status": "FAIL", "message": f"Expected 0.0 for non-existent location, got {balance}"}
            
    except Exception as e:
        return {"test": "balance_calculation", "status": "ERROR", "message": str(e)}


def _test_status_update_triggers() -> dict:
    """Test if status updates are called in key functions."""
    try:
        import inspect
        from logistics.warehousing.api import post_pick, post_putaway, post_receiving, post_release
        
        # Check if status update is called in key functions
        functions_to_check = [post_pick, post_putaway, post_receiving, post_release]
        functions_with_status_update = []
        
        for func in functions_to_check:
            try:
                source = inspect.getsource(func)
                if "_set_sl_status_by_balance" in source:
                    functions_with_status_update.append(func.__name__)
            except:
                pass
        
        if len(functions_with_status_update) == len(functions_to_check):
            return {"test": "status_update_triggers", "status": "PASS", "message": f"All key functions call status update: {functions_with_status_update}"}
        else:
            return {"test": "status_update_triggers", "status": "FAIL", "message": f"Only {len(functions_with_status_update)}/{len(functions_to_check)} functions call status update"}
            
    except Exception as e:
        return {"test": "status_update_triggers", "status": "ERROR", "message": str(e)}


def _generate_test_summary(test_results) -> dict:
    """Generate summary of test results."""
    total_tests = len(test_results)
    passed_tests = len([r for r in test_results if r.get("status") == "PASS"])
    failed_tests = len([r for r in test_results if r.get("status") == "FAIL"])
    error_tests = len([r for r in test_results if r.get("status") == "ERROR"])
    
    return {
        "total_tests": total_tests,
        "passed": passed_tests,
        "failed": failed_tests,
        "errors": error_tests,
        "success_rate": f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
    }


@frappe.whitelist()
def test_specific_location_status(location_name: str) -> dict:
    """
    Test status update for a specific location.
    """
    try:
        from logistics.warehousing.api import _set_sl_status_by_balance, _sl_balance, _get_sl
        
        # Get current status
        location = _get_sl(location_name)
        if not location:
            return {"error": f"Location {location_name} not found"}
        
        current_status = getattr(location, "status", "Unknown")
        balance = _sl_balance(location_name)
        expected_status = "In Use" if balance > 0 else "Available"
        
        # Test status update
        _set_sl_status_by_balance(location_name)
        
        # Refresh and check new status
        location.reload()
        new_status = getattr(location, "status", "Unknown")
        
        return {
            "location_name": location_name,
            "current_status": current_status,
            "new_status": new_status,
            "balance": balance,
            "expected_status": expected_status,
            "status_updated": current_status != new_status,
            "status_correct": new_status == expected_status
        }
        
    except Exception as e:
        frappe.log_error(f"Error in test_specific_location_status: {str(e)}")
        return {"error": str(e)}