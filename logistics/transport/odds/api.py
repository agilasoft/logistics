# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Public API endpoints for ODDS integration

Provides whitelisted methods for creating orders, getting quotations,
and managing ODDS deliveries from all logistics modules.
"""

import frappe
from frappe import _
from typing import Dict, Any
from .service import ODDSService
from .exceptions import (
    ODDSException,
    ODDSQuotationExpiredException,
    ODDSProviderNotSupportedException
)


@frappe.whitelist()
def get_odds_quotation(
    doctype: str, 
    docname: str, 
    provider: str = None
) -> Dict[str, Any]:
    """
    Get ODDS quotation for any supported doctype
    
    Args:
        doctype: Source doctype
        docname: Source document name
        provider: Provider code (optional, uses default if not provided)
        
    Returns:
        Quotation data
    """
    try:
        service = ODDSService(provider_code=provider)
        quotation = service.get_quotation(doctype, docname)
        
        return {
            "success": True,
            "data": quotation
        }
        
    except ODDSQuotationExpiredException as e:
        return {
            "success": False,
            "error": "Quotation expired",
            "message": str(e)
        }
    except ODDSProviderNotSupportedException as e:
        return {
            "success": False,
            "error": "Provider not supported",
            "message": str(e)
        }
    except Exception as e:
        frappe.log_error(
            f"Error getting ODDS quotation for {doctype} {docname}: {str(e)}",
            "ODDS API Error"
        )
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def create_odds_order(
    doctype: str, 
    docname: str, 
    quotation_id: str = None,
    provider: str = None
) -> Dict[str, Any]:
    """
    Create ODDS order from any supported doctype
    
    Args:
        doctype: Source doctype
        docname: Source document name
        quotation_id: Optional quotation ID (if not provided, will get new quotation)
        provider: Provider code (optional, uses default if not provided)
        
    Returns:
        Order data
    """
    try:
        service = ODDSService(provider_code=provider)
        order = service.create_order(doctype, docname, quotation_id)
        
        return {
            "success": True,
            "data": order,
            "message": _("ODDS order created successfully")
        }
        
    except ODDSQuotationExpiredException:
        # Retry with new quotation
        try:
            service = ODDSService(provider_code=provider)
            order = service.create_order(doctype, docname, None, auto_get_quotation=True)
            return {
                "success": True,
                "data": order,
                "message": _("ODDS order created successfully (with new quotation)")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    except ODDSProviderNotSupportedException as e:
        return {
            "success": False,
            "error": "Provider not supported",
            "message": str(e)
        }
    except Exception as e:
        frappe.log_error(
            f"Error creating ODDS order for {doctype} {docname}: {str(e)}",
            "ODDS API Error"
        )
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def get_odds_order_status(order_id: str, provider: str = None) -> Dict[str, Any]:
    """
    Get current order status from ODDS provider
    
    Args:
        order_id: ODDS order ID
        provider: Provider code (optional, uses default if not provided)
        
    Returns:
        Order status data
    """
    try:
        service = ODDSService(provider_code=provider)
        order_data = service.get_order_details(order_id)
        
        return {
            "success": True,
            "data": order_data
        }
        
    except Exception as e:
        frappe.log_error(
            f"Error getting ODDS order status {order_id}: {str(e)}",
            "ODDS API Error"
        )
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def sync_odds_order_status(order_id: str, provider: str = None) -> Dict[str, Any]:
    """
    Manually sync order status from ODDS provider
    
    Args:
        order_id: ODDS order ID
        provider: Provider code (optional, uses default if not provided)
        
    Returns:
        Updated order data
    """
    try:
        service = ODDSService(provider_code=provider)
        order_data = service.sync_order_status(order_id)
        
        return {
            "success": True,
            "data": order_data,
            "message": _("Order status synced successfully")
        }
        
    except Exception as e:
        frappe.log_error(
            f"Error syncing ODDS order status {order_id}: {str(e)}",
            "ODDS API Error"
        )
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def cancel_odds_order(order_id: str, provider: str = None) -> Dict[str, Any]:
    """
    Cancel ODDS order
    
    Args:
        order_id: ODDS order ID
        provider: Provider code (optional, uses default if not provided)
        
    Returns:
        Cancellation response
    """
    try:
        service = ODDSService(provider_code=provider)
        response = service.cancel_order(order_id)
        
        return {
            "success": True,
            "data": response,
            "message": _("Order cancelled successfully")
        }
        
    except Exception as e:
        frappe.log_error(
            f"Error cancelling ODDS order {order_id}: {str(e)}",
            "ODDS API Error"
        )
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def get_available_providers() -> Dict[str, Any]:
    """
    Get list of available ODDS providers
    
    Returns:
        List of available providers
    """
    try:
        from .providers import get_all_providers
        
        providers = get_all_providers()
        provider_list = [
            {
                "code": code,
                "name": provider.provider_name
            }
            for code, provider in providers.items()
        ]
        
        return {
            "success": True,
            "data": provider_list
        }
    except Exception as e:
        frappe.log_error(
            f"Error getting available providers: {str(e)}",
            "ODDS API Error"
        )
        return {
            "success": False,
            "error": str(e)
        }

