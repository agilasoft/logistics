# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Webhook handler for Lalamove integration

Handles incoming webhooks from Lalamove and updates order status
across all logistics modules.
"""

import frappe
import hmac
import hashlib
from frappe import _
from typing import Dict, Any
from .service import LalamoveService
from .exceptions import LalamoveException


@frappe.whitelist(allow_guest=True)
def handle_webhook():
    """
    Handle incoming webhook from Lalamove
    Updates status for all supported doctypes across all modules
    """
    try:
        # Get webhook data
        data = frappe.request.get_json()
        if not data:
            frappe.throw("Invalid webhook payload")
        
        # Validate webhook signature
        if not _validate_webhook_signature():
            frappe.throw("Invalid webhook signature", exc=frappe.PermissionError)
        
        # Process webhook event
        event_type = data.get("event")
        order_id = data.get("orderId")
        
        if not order_id:
            frappe.throw("Order ID is missing from webhook")
        
        # Get service instance
        service = LalamoveService()
        
        # Handle different event types
        if event_type == "ORDER_STATUS_CHANGED":
            _handle_order_status_changed(service, order_id, data)
        elif event_type == "DRIVER_ASSIGNED":
            _handle_driver_assigned(service, order_id, data)
        elif event_type == "ORDER_AMOUNT_CHANGED":
            _handle_order_amount_changed(service, order_id, data)
        elif event_type == "ORDER_REPLACED":
            _handle_order_replaced(service, order_id, data)
        elif event_type == "ORDER_EDITED":
            _handle_order_edited(service, order_id, data)
        elif event_type == "WALLET_BALANCE_CHANGED":
            _handle_wallet_balance_changed(service, data)
        else:
            frappe.log_error(
                f"Unknown webhook event type: {event_type}",
                "Lalamove Webhook Error"
            )
        
        # Return success response
        return {"status": "success", "message": "Webhook processed successfully"}
        
    except Exception as e:
        frappe.log_error(
            f"Error processing Lalamove webhook: {str(e)}",
            "Lalamove Webhook Error"
        )
        frappe.throw(f"Webhook processing failed: {str(e)}")


def _validate_webhook_signature() -> bool:
    """
    Validate webhook signature
    
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        settings = frappe.get_single("Lalamove Settings")
        webhook_secret = frappe.utils.password.get_decrypted_password(
            "Lalamove Settings",
            "Lalamove Settings",
            "webhook_secret",
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
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            body.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(signature, expected_signature)
        
    except Exception as e:
        frappe.log_error(
            f"Error validating webhook signature: {str(e)}",
            "Lalamove Webhook Validation Error"
        )
        return False


def _handle_order_status_changed(service: LalamoveService, order_id: str, data: Dict[str, Any]):
    """Handle ORDER_STATUS_CHANGED event"""
    try:
        # Sync order status
        service.sync_order_status(order_id)
        
        frappe.logger().info(f"Order status updated for Lalamove order {order_id}")
        
    except Exception as e:
        frappe.log_error(
            f"Error handling ORDER_STATUS_CHANGED for {order_id}: {str(e)}",
            "Lalamove Webhook Error"
        )


def _handle_driver_assigned(service: LalamoveService, order_id: str, data: Dict[str, Any]):
    """Handle DRIVER_ASSIGNED event"""
    try:
        # Sync order to get driver details
        service.sync_order_status(order_id)
        
        frappe.logger().info(f"Driver assigned for Lalamove order {order_id}")
        
    except Exception as e:
        frappe.log_error(
            f"Error handling DRIVER_ASSIGNED for {order_id}: {str(e)}",
            "Lalamove Webhook Error"
        )


def _handle_order_amount_changed(service: LalamoveService, order_id: str, data: Dict[str, Any]):
    """Handle ORDER_AMOUNT_CHANGED event"""
    try:
        # Sync order to get updated price
        service.sync_order_status(order_id)
        
        frappe.logger().info(f"Order amount changed for Lalamove order {order_id}")
        
    except Exception as e:
        frappe.log_error(
            f"Error handling ORDER_AMOUNT_CHANGED for {order_id}: {str(e)}",
            "Lalamove Webhook Error"
        )


def _handle_order_replaced(service: LalamoveService, order_id: str, data: Dict[str, Any]):
    """Handle ORDER_REPLACED event"""
    try:
        # Get new order ID from data
        new_order_id = data.get("newOrderId")
        
        if new_order_id:
            # Update Lalamove Order record with new order ID
            order = frappe.get_doc("Lalamove Order", {"lalamove_order_id": order_id})
            order.lalamove_order_id = new_order_id
            order.save(ignore_permissions=True)
            frappe.db.commit()
        
        frappe.logger().info(f"Order replaced for Lalamove order {order_id}")
        
    except Exception as e:
        frappe.log_error(
            f"Error handling ORDER_REPLACED for {order_id}: {str(e)}",
            "Lalamove Webhook Error"
        )


def _handle_order_edited(service: LalamoveService, order_id: str, data: Dict[str, Any]):
    """Handle ORDER_EDITED event"""
    try:
        # Sync order to get updated details
        service.sync_order_status(order_id)
        
        frappe.logger().info(f"Order edited for Lalamove order {order_id}")
        
    except Exception as e:
        frappe.log_error(
            f"Error handling ORDER_EDITED for {order_id}: {str(e)}",
            "Lalamove Webhook Error"
        )


def _handle_wallet_balance_changed(service: LalamoveService, data: Dict[str, Any]):
    """Handle WALLET_BALANCE_CHANGED event"""
    try:
        # Log wallet balance change
        balance = data.get("balance")
        frappe.logger().info(f"Lalamove wallet balance changed: {balance}")
        
        # Could update settings or send notification
        # Implementation depends on requirements
        
    except Exception as e:
        frappe.log_error(
            f"Error handling WALLET_BALANCE_CHANGED: {str(e)}",
            "Lalamove Webhook Error"
        )


