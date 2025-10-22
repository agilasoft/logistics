# -*- coding: utf-8 -*-
"""
Test the _set_sl_status_by_balance function directly.
"""

import frappe
from frappe import _


@frappe.whitelist()
def test_status_function() -> dict:
    """
    Test the _set_sl_status_by_balance function directly.
    """
    try:
        from logistics.warehousing.api import _set_sl_status_by_balance, _sl_balance, _get_sl, _sl_fields
        
        # Check if status field exists
        sl_fields = _sl_fields()
        has_status_field = "status" in sl_fields
        
        if not has_status_field:
            return {"error": "Storage Location doctype doesn't have 'status' field"}
        
        # Get a test location
        locations = frappe.db.sql("SELECT name FROM `tabStorage Location` LIMIT 1", as_dict=True)
        if not locations:
            return {"error": "No storage locations found"}
        
        test_location = locations[0]["name"]
        
        # Get current status and balance
        location = _get_sl(test_location)
        current_status = getattr(location, "status", "Unknown")
        balance = _sl_balance(test_location)
        expected_status = "In Use" if balance > 0 else "Available"
        
        # Test the function step by step
        result = {
            "test_location": test_location,
            "current_status": current_status,
            "balance": balance,
            "expected_status": expected_status,
            "has_status_field": has_status_field,
            "status_needs_update": current_status != expected_status
        }
        
        # Call the function
        _set_sl_status_by_balance(test_location)
        
        # Check if status was updated
        location.reload()
        new_status = getattr(location, "status", "Unknown")
        
        result.update({
            "new_status": new_status,
            "status_updated": current_status != new_status,
            "status_correct": new_status == expected_status
        })
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Error in test_status_function: {str(e)}")
        return {"error": str(e)}


@frappe.whitelist()
def test_status_function_with_commit() -> dict:
    """
    Test the _set_sl_status_by_balance function with explicit commit.
    """
    try:
        from logistics.warehousing.api import _set_sl_status_by_balance, _sl_balance, _get_sl, _sl_fields
        
        # Check if status field exists
        sl_fields = _sl_fields()
        has_status_field = "status" in sl_fields
        
        if not has_status_field:
            return {"error": "Storage Location doctype doesn't have 'status' field"}
        
        # Get a test location
        locations = frappe.db.sql("SELECT name FROM `tabStorage Location` LIMIT 1", as_dict=True)
        if not locations:
            return {"error": "No storage locations found"}
        
        test_location = locations[0]["name"]
        
        # Get current status and balance
        location = _get_sl(test_location)
        current_status = getattr(location, "status", "Unknown")
        balance = _sl_balance(test_location)
        expected_status = "In Use" if balance > 0 else "Available"
        
        # Test the function step by step
        result = {
            "test_location": test_location,
            "current_status": current_status,
            "balance": balance,
            "expected_status": expected_status,
            "has_status_field": has_status_field,
            "status_needs_update": current_status != expected_status
        }
        
        # Call the function
        _set_sl_status_by_balance(test_location)
        
        # Explicit commit
        frappe.db.commit()
        
        # Check if status was updated
        location.reload()
        new_status = getattr(location, "status", "Unknown")
        
        result.update({
            "new_status": new_status,
            "status_updated": current_status != new_status,
            "status_correct": new_status == expected_status
        })
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Error in test_status_function_with_commit: {str(e)}")
        return {"error": str(e)}
