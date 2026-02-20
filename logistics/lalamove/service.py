# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Business logic service for Lalamove integration

Provides high-level methods for interacting with Lalamove API
across all logistics modules.
"""

import frappe
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from .client import LalamoveAPIClient
from .mapper import LalamoveMapper
from .exceptions import (
    LalamoveException,
    LalamoveQuotationExpiredException,
    LalamoveOrderException
)


class LalamoveService:
    """
    Business logic service for Lalamove integration
    Supports all logistics modules: Transport, Warehousing, Air Freight, Sea Freight
    """
    
    def __init__(self):
        self.client = None
        self.mapper = LalamoveMapper()
    
    def _get_client(self) -> LalamoveAPIClient:
        """Get or create API client"""
        if self.client is None:
            self.client = LalamoveAPIClient()
        return self.client
    
    def get_quotation(self, doctype: str, docname: str) -> Dict[str, Any]:
        """
        Get quotation for any supported doctype
        
        Args:
            doctype: Source doctype
            docname: Source document name
            
        Returns:
            Quotation data including quotationId
        """
        try:
            # Map to quotation request
            quotation_request = self.mapper.map_to_quotation_request(doctype, docname)
            
            # Get quotation from Lalamove
            client = self._get_client()
            response = client.get_quotation(quotation_request)
            
            # Cache quotation
            self._cache_quotation(doctype, docname, response)
            
            return response
            
        except Exception as e:
            frappe.log_error(
                f"Error getting Lalamove quotation for {doctype} {docname}: {str(e)}",
                "Lalamove Quotation Error"
            )
            raise
    
    def get_quotation_details(self, quotation_id: str) -> Dict[str, Any]:
        """
        Get quotation details
        
        Args:
            quotation_id: Quotation ID
            
        Returns:
            Quotation details
        """
        client = self._get_client()
        return client.get_quotation_details(quotation_id)
    
    def create_order(
        self, 
        doctype: str, 
        docname: str, 
        quotation_id: str = None,
        auto_get_quotation: bool = True
    ) -> Dict[str, Any]:
        """
        Create Lalamove order from any supported doctype
        
        Args:
            doctype: Source doctype
            docname: Source document name
            quotation_id: Quotation ID (if None, will get new quotation)
            auto_get_quotation: If True and quotation_id is None, get quotation automatically
            
        Returns:
            Order data including orderId
        """
        try:
            client = self._get_client()
            
            # Get quotation if not provided
            if not quotation_id:
                if auto_get_quotation:
                    quotation_response = self.get_quotation(doctype, docname)
                    quotation_id = quotation_response.get("data", {}).get("quotationId")
                    if not quotation_id:
                        raise LalamoveException("Failed to get quotation ID from response")
                else:
                    raise ValueError("quotation_id is required when auto_get_quotation is False")
            
            # Verify quotation is still valid
            quotation = self._get_cached_quotation(quotation_id)
            if quotation and not self._is_quotation_valid(quotation):
                # Get new quotation
                quotation_response = self.get_quotation(doctype, docname)
                quotation_id = quotation_response.get("data", {}).get("quotationId")
            
            # Place order
            order_response = client.place_order(quotation_id)
            
            # Store order
            self._store_order(doctype, docname, quotation_id, order_response)
            
            return order_response
            
        except LalamoveQuotationExpiredException:
            # Retry with new quotation
            if auto_get_quotation:
                quotation_response = self.get_quotation(doctype, docname)
                quotation_id = quotation_response.get("data", {}).get("quotationId")
                order_response = client.place_order(quotation_id)
                self._store_order(doctype, docname, quotation_id, order_response)
                return order_response
            raise
        except Exception as e:
            frappe.log_error(
                f"Error creating Lalamove order for {doctype} {docname}: {str(e)}",
                "Lalamove Order Creation Error"
            )
            raise
    
    def get_order_details(self, lalamove_order_id: str) -> Dict[str, Any]:
        """
        Get order details from Lalamove
        
        Args:
            lalamove_order_id: Lalamove order ID
            
        Returns:
            Order details
        """
        client = self._get_client()
        return client.get_order_details(lalamove_order_id)
    
    def sync_order_status(self, lalamove_order_id: str) -> Dict[str, Any]:
        """
        Sync order status from Lalamove and update local records
        
        Args:
            lalamove_order_id: Lalamove order ID
            
        Returns:
            Updated order data
        """
        try:
            # Get order details from Lalamove
            order_data = self.get_order_details(lalamove_order_id)
            
            # Update local Lalamove Order record
            self._update_lalamove_order(lalamove_order_id, order_data)
            
            # Update source document status
            self._update_source_document_status(lalamove_order_id, order_data)
            
            return order_data
            
        except Exception as e:
            frappe.log_error(
                f"Error syncing Lalamove order status {lalamove_order_id}: {str(e)}",
                "Lalamove Status Sync Error"
            )
            raise
    
    def cancel_order(self, lalamove_order_id: str) -> Dict[str, Any]:
        """
        Cancel Lalamove order
        
        Args:
            lalamove_order_id: Lalamove order ID
            
        Returns:
            Cancellation response
        """
        try:
            client = self._get_client()
            response = client.cancel_order(lalamove_order_id)
            
            # Update local records
            self.sync_order_status(lalamove_order_id)
            
            return response
            
        except Exception as e:
            frappe.log_error(
                f"Error cancelling Lalamove order {lalamove_order_id}: {str(e)}",
                "Lalamove Order Cancellation Error"
            )
            raise
    
    def change_driver(self, lalamove_order_id: str) -> Dict[str, Any]:
        """Request driver change"""
        client = self._get_client()
        return client.change_driver(lalamove_order_id)
    
    def add_priority_fee(self, lalamove_order_id: str) -> Dict[str, Any]:
        """Add priority fee to order"""
        client = self._get_client()
        return client.add_priority_fee(lalamove_order_id)
    
    # Helper methods
    
    def _cache_quotation(self, doctype: str, docname: str, quotation_response: Dict[str, Any]):
        """Cache quotation in Lalamove Quotation doctype"""
        try:
            data = quotation_response.get("data", {})
            quotation_id = data.get("quotationId")
            
            if not quotation_id:
                return
            
            # Check if quotation already exists
            existing = frappe.db.exists("Lalamove Quotation", {"quotation_id": quotation_id})
            
            if existing:
                # Update existing
                quotation = frappe.get_doc("Lalamove Quotation", existing)
            else:
                # Create new
                quotation = frappe.new_doc("Lalamove Quotation")
                quotation.quotation_id = quotation_id
            
            # Update fields
            quotation.source_doctype = doctype
            quotation.source_docname = docname
            
            # Set module-specific link
            if doctype == "Transport Order":
                quotation.transport_order = docname
            elif doctype == "Transport Job":
                quotation.transport_job = docname
            elif doctype == "Transport Leg":
                quotation.transport_leg = docname
            elif doctype == "Warehouse Job":
                quotation.warehouse_job = docname
            elif doctype == "Air Shipment":
                quotation.air_shipment = docname
            elif doctype == "Air Booking":
                quotation.air_booking = docname
            elif doctype == "Sea Shipment":
                quotation.sea_shipment = docname
            elif doctype == "Sea Booking":
                quotation.sea_booking = docname
            
            quotation.price = data.get("priceBreakdown", {}).get("total", 0)
            quotation.currency = data.get("priceBreakdown", {}).get("currency", "HKD")
            quotation.service_type = data.get("serviceType")
            quotation.expires_at = data.get("expiresAt")
            quotation.price_breakdown = frappe.as_json(data.get("priceBreakdown", {}))
            quotation.stops = frappe.as_json(data.get("stops", []))
            quotation.item = frappe.as_json(data.get("item", {}))
            quotation.distance = data.get("distance", 0)
            quotation.valid = True
            
            quotation.save(ignore_permissions=True)
            frappe.db.commit()
            
        except Exception as e:
            frappe.log_error(
                f"Error caching quotation: {str(e)}",
                "Lalamove Quotation Cache Error"
            )
    
    def _get_cached_quotation(self, quotation_id: str) -> Optional[Dict[str, Any]]:
        """Get cached quotation"""
        try:
            quotation = frappe.get_doc("Lalamove Quotation", {"quotation_id": quotation_id})
            return {
                "quotation_id": quotation.quotation_id,
                "expires_at": quotation.expires_at,
                "valid": quotation.valid
            }
        except Exception:
            return None
    
    def _is_quotation_valid(self, quotation: Dict[str, Any]) -> bool:
        """Check if quotation is still valid"""
        if not quotation.get("valid"):
            return False
        
        expires_at = quotation.get("expires_at")
        if not expires_at:
            return False
        
        try:
            expiry_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            return datetime.now(expiry_time.tzinfo) < expiry_time
        except Exception:
            return False
    
    def _store_order(
        self, 
        doctype: str, 
        docname: str, 
        quotation_id: str, 
        order_response: Dict[str, Any]
    ):
        """Store order in Lalamove Order doctype"""
        try:
            data = order_response.get("data", {})
            order_id = data.get("orderId")
            
            if not order_id:
                return
            
            # Create or update Lalamove Order
            existing = frappe.db.exists("Lalamove Order", {"lalamove_order_id": order_id})
            
            if existing:
                order = frappe.get_doc("Lalamove Order", existing)
            else:
                order = frappe.new_doc("Lalamove Order")
                order.lalamove_order_id = order_id
            
            # Update fields
            order.quotation_id = quotation_id
            order.source_doctype = doctype
            order.source_docname = docname
            
            # Set module-specific links
            if doctype == "Transport Order":
                order.transport_order = docname
            elif doctype == "Transport Job":
                order.transport_job = docname
            elif doctype == "Transport Leg":
                order.transport_leg = docname
            elif doctype == "Warehouse Job":
                order.warehouse_job = docname
            elif doctype == "Air Shipment":
                order.air_shipment = docname
            elif doctype == "Air Booking":
                order.air_booking = docname
            elif doctype == "Sea Shipment":
                order.sea_shipment = docname
            elif doctype == "Sea Booking":
                order.sea_booking = docname
            
            order.status = data.get("status", "ASSIGNING_DRIVER")
            order.price = data.get("price", 0)
            order.currency = data.get("currency", "HKD")
            
            # Update from quotation if available
            quotation = frappe.db.get_value("Lalamove Quotation", {"quotation_id": quotation_id}, "name")
            if quotation:
                order.quotation_id = quotation
            
            order.save(ignore_permissions=True)
            frappe.db.commit()
            
            # Update source document
            self._update_source_document_lalamove_order(doctype, docname, order.name)
            
        except Exception as e:
            frappe.log_error(
                f"Error storing Lalamove order: {str(e)}",
                "Lalamove Order Storage Error"
            )
    
    def _update_lalamove_order(self, lalamove_order_id: str, order_data: Dict[str, Any]):
        """Update Lalamove Order record with latest data"""
        try:
            order = frappe.get_doc("Lalamove Order", {"lalamove_order_id": lalamove_order_id})
            
            data = order_data.get("data", {})
            
            order.status = data.get("status", order.status)
            order.price = data.get("price", order.price)
            order.distance = data.get("distance", order.distance)
            
            # Driver information
            driver = data.get("driver", {})
            if driver:
                order.driver_name = driver.get("name")
                order.driver_phone = driver.get("phone")
                order.driver_photo = driver.get("photo")
            
            # Vehicle information
            vehicle = data.get("vehicle", {})
            if vehicle:
                order.vehicle_type = vehicle.get("type")
                order.vehicle_number = vehicle.get("vehicleNumber")
            
            # Timestamps
            if data.get("scheduleAt"):
                order.scheduled_at = data.get("scheduleAt")
            if data.get("completedAt"):
                order.completed_at = data.get("completedAt")
            
            # Metadata
            order.metadata = frappe.as_json(data)
            
            order.save(ignore_permissions=True)
            frappe.db.commit()
            
        except Exception as e:
            frappe.log_error(
                f"Error updating Lalamove Order {lalamove_order_id}: {str(e)}",
                "Lalamove Order Update Error"
            )
    
    def _update_source_document_lalamove_order(self, doctype: str, docname: str, lalamove_order_name: str):
        """Update source document with Lalamove Order reference"""
        try:
            if frappe.db.exists(doctype, docname):
                frappe.db.set_value(
                    doctype,
                    docname,
                    "lalamove_order",
                    lalamove_order_name,
                    update_modified=False
                )
                frappe.db.commit()
        except Exception as e:
            frappe.log_error(
                f"Error updating source document {doctype} {docname}: {str(e)}",
                "Lalamove Source Document Update Error"
            )
    
    def _update_source_document_status(self, lalamove_order_id: str, order_data: Dict[str, Any]):
        """Update source document status based on Lalamove order status"""
        try:
            order = frappe.get_doc("Lalamove Order", {"lalamove_order_id": lalamove_order_id})
            
            if not order.source_doctype or not order.source_docname:
                return
            
            status = order_data.get("data", {}).get("status", "")
            
            # Map Lalamove status to module-specific status
            # This is a simplified mapping - can be enhanced per module
            if status == "COMPLETED":
                # Update source document status if applicable
                # Implementation depends on each module's status field
                pass
            elif status == "CANCELLED":
                # Update source document status
                pass
            
        except Exception as e:
            frappe.log_error(
                f"Error updating source document status: {str(e)}",
                "Lalamove Status Update Error"
            )


