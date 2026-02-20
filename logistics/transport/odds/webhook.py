# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Webhook handler for ODDS integration

Handles incoming webhooks from ODDS providers and updates order status
across all logistics modules.
"""

import frappe
from frappe import _
from typing import Dict, Any
from .service import ODDSService
from .exceptions import ODDSException


@frappe.whitelist(allow_guest=True)
def handle_webhook(provider: str = None):
    """
    Handle incoming webhook from ODDS provider
    
    Args:
        provider: Provider code (optional, can be determined from webhook data)
    
    Updates status for all supported doctypes across all modules
    """
    try:
        # Get webhook data
        data = frappe.request.get_json()
        if not data:
            frappe.throw("Invalid webhook payload")
        
        # Determine provider if not specified
        if not provider:
            provider = _detect_provider_from_webhook(data)
        
        if not provider:
            frappe.throw("Could not determine provider from webhook")
        
        # Validate webhook signature
        if not _validate_webhook_signature(provider, data):
            frappe.throw("Invalid webhook signature", exc=frappe.PermissionError)
        
        # Process webhook event
        event_type = data.get("event") or data.get("event_type") or data.get("type")
        order_id = data.get("orderId") or data.get("order_id") or data.get("id")
        
        if not order_id:
            frappe.throw("Order ID is missing from webhook")
        
        # Get service instance
        service = ODDSService(provider_code=provider)
        
        # Handle different event types
        if event_type in ["ORDER_STATUS_CHANGED", "order_status_changed", "status_changed"]:
            _handle_order_status_changed(service, order_id, data)
        elif event_type in ["DRIVER_ASSIGNED", "driver_assigned"]:
            _handle_driver_assigned(service, order_id, data)
        elif event_type in ["ORDER_AMOUNT_CHANGED", "order_amount_changed"]:
            _handle_order_amount_changed(service, order_id, data)
        elif event_type in ["ORDER_REPLACED", "order_replaced"]:
            _handle_order_replaced(service, order_id, data)
        elif event_type in ["ORDER_EDITED", "order_edited"]:
            _handle_order_edited(service, order_id, data)
        else:
            frappe.log_error(
                f"Unknown webhook event type: {event_type} for provider {provider}",
                "ODDS Webhook Error"
            )
        
        # Return success response
        return {"status": "success", "message": "Webhook processed successfully"}
        
    except Exception as e:
        frappe.log_error(
            f"Error processing ODDS webhook: {str(e)}",
            "ODDS Webhook Error"
        )
        frappe.throw(f"Webhook processing failed: {str(e)}")


def _detect_provider_from_webhook(data: Dict[str, Any]) -> str:
    """Detect provider from webhook data"""
    # Check for provider-specific indicators
    if "lalamove" in str(data).lower() or "X-Lalamove" in str(frappe.request.headers):
        return "lalamove"
    elif "transportify" in str(data).lower() or "deliveree" in str(data).lower():
        return "transportify"
    elif "grab" in str(data).lower() or "grabexpress" in str(data).lower():
        return "grabexpress"
    elif "pandago" in str(data).lower():
        return "pandago"
    elif "ninjavan" in str(data).lower():
        return "ninjavan"
    
    # Try to get from order record
    order_id = data.get("orderId") or data.get("order_id") or data.get("id")
    if order_id:
        try:
            order_name = frappe.db.get_value("ODDS Order", {"order_id": str(order_id)}, "name")
            if order_name:
                order = frappe.get_doc("ODDS Order", order_name)
                return order.provider
        except Exception:
            pass
    
    return None


def _validate_webhook_signature(provider: str, data: Dict[str, Any]) -> bool:
    """
    Validate webhook signature
    
    Args:
        provider: Provider code
        data: Webhook data
        
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        settings = frappe.get_single("ODDS Settings")
        
        # Get provider-specific webhook secret
        if provider == "lalamove":
            webhook_secret = frappe.utils.password.get_decrypted_password(
                "ODDS Settings",
                "ODDS Settings",
                "lalamove_webhook_secret",
                raise_exception=False
            )
            
            if not webhook_secret:
                # If no secret configured, skip validation (not recommended for production)
                return True
            
            # Get signature from headers
            signature = frappe.request.headers.get("X-Lalamove-Signature")
            if not signature:
                return False
            
            # Get request body
            body = frappe.request.get_data(as_text=True)
            
            # Calculate expected signature
            import hmac
            import hashlib
            expected_signature = hmac.new(
                webhook_secret.encode('utf-8'),
                body.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            return hmac.compare_digest(signature, expected_signature)
        
        # Transportify/Deliveree webhook validation
        elif provider == "transportify":
            webhook_secret = frappe.utils.password.get_decrypted_password(
                "ODDS Settings",
                "ODDS Settings",
                "transportify_webhook_secret",
                raise_exception=False
            )
            
            if not webhook_secret:
                # If no secret configured, skip validation (not recommended for production)
                return True
            
            # Get signature from headers
            signature = frappe.request.headers.get("Authorization")
            if not signature:
                return False
            
            # Compare with configured secret
            return signature == webhook_secret
        
        # Add validation for other providers as needed
        # For now, return True for other providers (should be implemented)
        return True
        
    except Exception as e:
        frappe.log_error(
            f"Error validating webhook signature: {str(e)}",
            "ODDS Webhook Validation Error"
        )
        return False


def _handle_order_status_changed(service: ODDSService, order_id: str, data: Dict[str, Any]):
    """Handle ORDER_STATUS_CHANGED event"""
    try:
        service.sync_order_status(order_id)
        frappe.logger().info(f"Order status updated for ODDS order {order_id}")
    except Exception as e:
        frappe.log_error(
            f"Error handling ORDER_STATUS_CHANGED for {order_id}: {str(e)}",
            "ODDS Webhook Error"
        )


def _handle_driver_assigned(service: ODDSService, order_id: str, data: Dict[str, Any]):
    """Handle DRIVER_ASSIGNED event"""
    try:
        service.sync_order_status(order_id)
        frappe.logger().info(f"Driver assigned for ODDS order {order_id}")
    except Exception as e:
        frappe.log_error(
            f"Error handling DRIVER_ASSIGNED for {order_id}: {str(e)}",
            "ODDS Webhook Error"
        )


def _handle_order_amount_changed(service: ODDSService, order_id: str, data: Dict[str, Any]):
    """Handle ORDER_AMOUNT_CHANGED event"""
    try:
        service.sync_order_status(order_id)
        frappe.logger().info(f"Order amount changed for ODDS order {order_id}")
    except Exception as e:
        frappe.log_error(
            f"Error handling ORDER_AMOUNT_CHANGED for {order_id}: {str(e)}",
            "ODDS Webhook Error"
        )


def _handle_order_replaced(service: ODDSService, order_id: str, data: Dict[str, Any]):
    """Handle ORDER_REPLACED event"""
    try:
        new_order_id = data.get("newOrderId") or data.get("new_order_id")
        
        if new_order_id:
            # Update ODDS Order record with new order ID
            order = frappe.get_doc("ODDS Order", {"order_id": order_id})
            order.order_id = new_order_id
            order.save(ignore_permissions=True)
            frappe.db.commit()
        
        frappe.logger().info(f"Order replaced for ODDS order {order_id}")
    except Exception as e:
        frappe.log_error(
            f"Error handling ORDER_REPLACED for {order_id}: {str(e)}",
            "ODDS Webhook Error"
        )


def _handle_order_edited(service: ODDSService, order_id: str, data: Dict[str, Any]):
    """Handle ORDER_EDITED event"""
    try:
        service.sync_order_status(order_id)
        frappe.logger().info(f"Order edited for ODDS order {order_id}")
    except Exception as e:
        frappe.log_error(
            f"Error handling ORDER_EDITED for {order_id}: {str(e)}",
            "ODDS Webhook Error"
        )

