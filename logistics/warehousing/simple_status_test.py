# -*- coding: utf-8 -*-
"""
Simple test to verify storage location status update.
"""

import frappe
from frappe import _


@frappe.whitelist()
def test_simple_status_update() -> dict:
    """
    Simple test to verify status update mechanism.
    """
    try:
        from logistics.warehousing.api import _set_sl_status_by_balance, _sl_balance, _get_sl, _sl_fields
        
        # Check if status field exists
        sl_fields = _sl_fields()
        has_status_field = "status" in sl_fields
        
        if not has_status_field:
            return {"error": "Storage Location doctype doesn't have 'status' field"}
        
        # Get a test location (first available location)
        locations = frappe.db.sql("SELECT name FROM `tabStorage Location` LIMIT 1", as_dict=True)
        if not locations:
            return {"error": "No storage locations found"}
        
        test_location = locations[0]["name"]
        
        # Get current status and balance
        location = _get_sl(test_location)
        current_status = getattr(location, "status", "Unknown")
        balance = _sl_balance(test_location)
        
        # Test status update
        _set_sl_status_by_balance(test_location)
        
        # Refresh and check new status
        location.reload()
        new_status = getattr(location, "status", "Unknown")
        
        return {
            "test_location": test_location,
            "current_status": current_status,
            "new_status": new_status,
            "balance": balance,
            "expected_status": "In Use" if balance > 0 else "Available",
            "status_updated": current_status != new_status,
            "status_correct": new_status == ("In Use" if balance > 0 else "Available"),
            "has_status_field": has_status_field
        }
        
    except Exception as e:
        frappe.log_error(f"Error in test_simple_status_update: {str(e)}")
        return {"error": str(e)}
