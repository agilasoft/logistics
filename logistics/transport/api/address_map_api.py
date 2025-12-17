# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
API endpoints for Address Map functionality
Provides properly decrypted Google Maps API key for client-side use
"""
import frappe
from frappe.utils.password import get_decrypted_password


@frappe.whitelist()
def get_google_maps_api_key():
    """
    Get the Google Maps API key for client-side use.
    This properly decrypts the Password field.
    
    Returns:
        dict: {
            "api_key": str or None,
            "has_key": bool
        }
    """
    try:
        # Get the API key using the same method as routing.py
        # For Single doctypes, both doctype and name are the same
        # This properly decrypts Password fields
        api_key = get_decrypted_password(
            "Transport Settings",
            "Transport Settings",
            "routing_google_api_key",
            raise_exception=False
        )
        
        # Also try alternative field names (for compatibility)
        if not api_key:
            for field_name in ["google_api_key", "google_maps_api_key", "maps_api_key"]:
                api_key = get_decrypted_password(
                    "Transport Settings",
                    "Transport Settings",
                    field_name,
                    raise_exception=False
                )
                if api_key:
                    break
        
        if api_key and len(api_key) > 10:
            return {
                "api_key": api_key,
                "has_key": True
            }
        else:
            return {
                "api_key": None,
                "has_key": False
            }
    except Exception as e:
        frappe.log_error(f"Error getting Google Maps API key: {str(e)}", "Address Map API")
        return {
            "api_key": None,
            "has_key": False,
            "error": str(e)
        }

