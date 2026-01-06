# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Public API endpoints for Lalamove integration

Provides whitelisted methods for creating orders, getting quotations,
and managing Lalamove deliveries from all logistics modules.
"""

import frappe
from frappe import _
from typing import Dict, Any
from logistics.lalamove.service import LalamoveService
from logistics.lalamove.exceptions import (
    LalamoveException,
    LalamoveQuotationExpiredException
)


@frappe.whitelist()
def get_lalamove_quotation(doctype: str, docname: str) -> Dict[str, Any]:
    """
    Get Lalamove quotation for any supported doctype
    Supports: Transport Order/Job/Leg, Warehouse Job, Air Shipment/Booking, Sea Shipment/Booking
    
    Args:
        doctype: Source doctype
        docname: Source document name
        
    Returns:
        Quotation data
    """
    try:
        service = LalamoveService()
        quotation = service.get_quotation(doctype, docname)
        
        return {
            "success": True,
            "data": quotation
        }
        
    except LalamoveQuotationExpiredException as e:
        return {
            "success": False,
            "error": "Quotation expired",
            "message": str(e)
        }
    except Exception as e:
        frappe.log_error(
            f"Error getting Lalamove quotation for {doctype} {docname}: {str(e)}",
            "Lalamove API Error"
        )
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def create_lalamove_order(
    doctype: str, 
    docname: str, 
    quotation_id: str = None
) -> Dict[str, Any]:
    """
    Create Lalamove order from any supported doctype
    Supports: Transport Order/Job/Leg, Warehouse Job, Air Shipment/Booking, Sea Shipment/Booking
    
    Args:
        doctype: Source doctype
        docname: Source document name
        quotation_id: Optional quotation ID (if not provided, will get new quotation)
        
    Returns:
        Order data
    """
    try:
        service = LalamoveService()
        order = service.create_order(doctype, docname, quotation_id)
        
        return {
            "success": True,
            "data": order,
            "message": _("Lalamove order created successfully")
        }
        
    except LalamoveQuotationExpiredException:
        # Retry with new quotation
        try:
            service = LalamoveService()
            order = service.create_order(doctype, docname, None, auto_get_quotation=True)
            return {
                "success": True,
                "data": order,
                "message": _("Lalamove order created successfully (with new quotation)")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    except Exception as e:
        frappe.log_error(
            f"Error creating Lalamove order for {doctype} {docname}: {str(e)}",
            "Lalamove API Error"
        )
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def get_lalamove_order_status(lalamove_order_id: str) -> Dict[str, Any]:
    """
    Get current order status from Lalamove
    
    Args:
        lalamove_order_id: Lalamove order ID
        
    Returns:
        Order status data
    """
    try:
        service = LalamoveService()
        order_data = service.get_order_details(lalamove_order_id)
        
        return {
            "success": True,
            "data": order_data
        }
        
    except Exception as e:
        frappe.log_error(
            f"Error getting Lalamove order status {lalamove_order_id}: {str(e)}",
            "Lalamove API Error"
        )
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def sync_lalamove_order_status(lalamove_order_id: str) -> Dict[str, Any]:
    """
    Manually sync order status from Lalamove
    
    Args:
        lalamove_order_id: Lalamove order ID
        
    Returns:
        Updated order data
    """
    try:
        service = LalamoveService()
        order_data = service.sync_order_status(lalamove_order_id)
        
        return {
            "success": True,
            "data": order_data,
            "message": _("Order status synced successfully")
        }
        
    except Exception as e:
        frappe.log_error(
            f"Error syncing Lalamove order status {lalamove_order_id}: {str(e)}",
            "Lalamove API Error"
        )
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def cancel_lalamove_order(lalamove_order_id: str) -> Dict[str, Any]:
    """
    Cancel Lalamove order
    
    Args:
        lalamove_order_id: Lalamove order ID
        
    Returns:
        Cancellation response
    """
    try:
        service = LalamoveService()
        response = service.cancel_order(lalamove_order_id)
        
        return {
            "success": True,
            "data": response,
            "message": _("Order cancelled successfully")
        }
        
    except Exception as e:
        frappe.log_error(
            f"Error cancelling Lalamove order {lalamove_order_id}: {str(e)}",
            "Lalamove API Error"
        )
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def change_lalamove_driver(lalamove_order_id: str) -> Dict[str, Any]:
    """
    Request driver change for Lalamove order
    
    Args:
        lalamove_order_id: Lalamove order ID
        
    Returns:
        Response data
    """
    try:
        service = LalamoveService()
        response = service.change_driver(lalamove_order_id)
        
        return {
            "success": True,
            "data": response,
            "message": _("Driver change requested successfully")
        }
        
    except Exception as e:
        frappe.log_error(
            f"Error changing driver for Lalamove order {lalamove_order_id}: {str(e)}",
            "Lalamove API Error"
        )
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def add_lalamove_priority_fee(lalamove_order_id: str) -> Dict[str, Any]:
    """
    Add priority fee to Lalamove order
    
    Args:
        lalamove_order_id: Lalamove order ID
        
    Returns:
        Response data
    """
    try:
        service = LalamoveService()
        response = service.add_priority_fee(lalamove_order_id)
        
        return {
            "success": True,
            "data": response,
            "message": _("Priority fee added successfully")
        }
        
    except Exception as e:
        frappe.log_error(
            f"Error adding priority fee for Lalamove order {lalamove_order_id}: {str(e)}",
            "Lalamove API Error"
        )
        return {
            "success": False,
            "error": str(e)
        }


