# -*- coding: utf-8 -*-
"""
Debug script to test storage location status update.
"""

import frappe
from frappe import _


@frappe.whitelist()
def debug_status_update(location_name: str) -> dict:
    """
    Debug status update for a specific location.
    """
    try:
        from logistics.warehousing.api import _set_sl_status_by_balance, _sl_balance, _get_sl, _sl_fields
        
        # Check if status field exists
        sl_fields = _sl_fields()
        has_status_field = "status" in sl_fields
        
        if not has_status_field:
            return {"error": "Storage Location doctype doesn't have 'status' field"}
        
        # Get current status and balance
        location = _get_sl(location_name)
        if not location:
            return {"error": f"Location {location_name} not found"}
        
        current_status = getattr(location, "status", "Unknown")
        balance = _sl_balance(location_name)
        expected_status = "In Use" if balance > 0 else "Available"
        
        # Debug info
        debug_info = {
            "location_name": location_name,
            "current_status": current_status,
            "balance": balance,
            "expected_status": expected_status,
            "has_status_field": has_status_field,
            "status_needs_update": current_status != expected_status
        }
        
        # Test status update
        _set_sl_status_by_balance(location_name)
        
        # Refresh and check new status
        location.reload()
        new_status = getattr(location, "status", "Unknown")
        
        debug_info.update({
            "new_status": new_status,
            "status_updated": current_status != new_status,
            "status_correct": new_status == expected_status
        })
        
        return debug_info
        
    except Exception as e:
        frappe.log_error(f"Error in debug_status_update: {str(e)}")
        return {"error": str(e)}


@frappe.whitelist()
def force_status_update(location_name: str) -> dict:
    """
    Force status update for a specific location.
    """
    try:
        from logistics.warehousing.api import _sl_balance, _get_sl
        
        # Get current status and balance
        location = _get_sl(location_name)
        if not location:
            return {"error": f"Location {location_name} not found"}
        
        current_status = getattr(location, "status", "Unknown")
        balance = _sl_balance(location_name)
        expected_status = "In Use" if balance > 0 else "Available"
        
        # Force update
        location.status = expected_status
        location.save(ignore_permissions=True)
        frappe.db.commit()
        
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
        frappe.log_error(f"Error in force_status_update: {str(e)}")
        return {"error": str(e)}
