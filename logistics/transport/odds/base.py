# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Base classes for ODDS (On-demand Delivery Services) integration

Provides abstract interfaces and base implementations for multiple delivery service providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import frappe
from .exceptions import ODDSException


class ODDSProvider(ABC):
    """
    Abstract base class for ODDS providers
    
    Each provider (Lalamove, Transportify, etc.) must implement this interface.
    """
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'Lalamove', 'Transportify')"""
        pass
    
    @property
    @abstractmethod
    def provider_code(self) -> str:
        """Return the provider code (e.g., 'lalamove', 'transportify')"""
        pass
    
    @abstractmethod
    def get_client(self, settings: Dict[str, Any] = None) -> 'ODDSClient':
        """Get or create API client for this provider"""
        pass
    
    @abstractmethod
    def get_mapper(self) -> 'ODDSMapper':
        """Get mapper instance for this provider"""
        pass
    
    @abstractmethod
    def get_settings_doctype(self) -> str:
        """Return the doctype name for provider settings"""
        pass


class ODDSClient(ABC):
    """
    Abstract base class for ODDS API clients
    
    Each provider must implement their specific API client.
    """
    
    def __init__(self, provider: str, settings: Dict[str, Any]):
        """
        Initialize ODDS client
        
        Args:
            provider: Provider name
            settings: Provider settings dictionary
        """
        self.provider = provider
        self.settings = settings
    
    @abstractmethod
    def get_quotation(self, quotation_request: Dict[str, Any]) -> Dict[str, Any]:
        """Get delivery quotation"""
        pass
    
    @abstractmethod
    def get_quotation_details(self, quotation_id: str) -> Dict[str, Any]:
        """Get quotation details"""
        pass
    
    @abstractmethod
    def place_order(self, quotation_id: str, order_request: Dict[str, Any] = None) -> Dict[str, Any]:
        """Place delivery order"""
        pass
    
    @abstractmethod
    def get_order_details(self, order_id: str) -> Dict[str, Any]:
        """Get order details"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel order"""
        pass
    
    @abstractmethod
    def get_driver_details(self, driver_id: str) -> Dict[str, Any]:
        """Get driver details"""
        pass


class ODDSMapper(ABC):
    """
    Abstract base class for ODDS data mappers
    
    Maps data between logistics modules and provider-specific API formats.
    """
    
    def __init__(self, provider: str):
        """
        Initialize ODDS mapper
        
        Args:
            provider: Provider name
        """
        self.provider = provider
        self.supported_doctypes = [
            "Transport Order",
            "Transport Job",
            "Transport Leg",
            "Warehouse Job",
            "Air Shipment",
            "Air Booking",
            "Sea Shipment",
            "Sea Booking"
        ]
    
    @abstractmethod
    def map_to_quotation_request(self, doctype: str, docname: str) -> Dict[str, Any]:
        """
        Map source document to provider-specific quotation request
        
        Args:
            doctype: Source doctype
            docname: Source document name
            
        Returns:
            Provider-specific quotation request dictionary
        """
        pass
    
    @abstractmethod
    def map_from_quotation_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map provider-specific quotation response to standard format
        
        Args:
            response: Provider-specific response
            
        Returns:
            Standardized quotation data
        """
        pass
    
    @abstractmethod
    def map_from_order_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map provider-specific order response to standard format
        
        Args:
            response: Provider-specific response
            
        Returns:
            Standardized order data
        """
        pass
    
    def _create_stop_from_address(self, address_name: str) -> Dict[str, Any]:
        """Create stop from Address doctype (common implementation)"""
        address = frappe.get_doc("Address", address_name)
        
        # Get coordinates
        coordinates = self._get_address_coordinates(address)
        
        stop = {
            "coordinates": {
                "lat": str(coordinates["lat"]),
                "lng": str(coordinates["lng"])
            },
            "address": self._format_address_string(address)
        }
        
        return stop
    
    def _get_address_coordinates(self, address) -> Dict[str, float]:
        """Get coordinates from address (common implementation)"""
        # Check if address has coordinates
        if hasattr(address, "latitude") and address.latitude and hasattr(address, "longitude") and address.longitude:
            return {
                "lat": float(address.latitude),
                "lng": float(address.longitude)
            }
        
        # Try to get from address_geo if available
        try:
            from logistics.address_geo import get_address_coordinates
            coords = get_address_coordinates(address.name)
            if coords:
                return coords
        except Exception:
            pass
        
        # Fallback: raise error (coordinates are required)
        raise ValueError(f"Address {address.name} does not have coordinates. Please geocode the address first.")
    
    def _format_address_string(self, address) -> str:
        """Format address as string (common implementation)"""
        parts = []
        if address.address_line1:
            parts.append(address.address_line1)
        if address.address_line2:
            parts.append(address.address_line2)
        if address.city:
            parts.append(address.city)
        if address.state:
            parts.append(address.state)
        if address.pincode:
            parts.append(address.pincode)
        if address.country:
            parts.append(address.country)
        
        return ", ".join(parts)


class ODDSService:
    """
    Generic service for ODDS integration
    
    Works with any provider through the provider interface.
    """
    
    def __init__(self, provider_code: str = None):
        """
        Initialize ODDS service
        
        Args:
            provider_code: Provider code (e.g., 'lalamove'). If None, uses default from settings.
        """
        self.provider_code = provider_code
        self.provider = None
        self.client = None
        self.mapper = None
    
    def _get_provider(self) -> ODDSProvider:
        """Get provider instance"""
        if self.provider is None:
            from .providers import get_provider
            
            if not self.provider_code:
                # Get default provider from settings
                try:
                    settings = frappe.get_single("ODDS Settings")
                    self.provider_code = settings.default_provider or "lalamove"
                except Exception:
                    # Fallback if settings don't exist yet
                    self.provider_code = "lalamove"
            
            self.provider = get_provider(self.provider_code)
        
        return self.provider
    
    def _get_client(self) -> ODDSClient:
        """Get or create API client"""
        if self.client is None:
            provider = self._get_provider()
            self.client = provider.get_client()
        return self.client
    
    def _get_mapper(self) -> ODDSMapper:
        """Get mapper instance"""
        if self.mapper is None:
            provider = self._get_provider()
            self.mapper = provider.get_mapper()
        return self.mapper
    
    def get_quotation(self, doctype: str, docname: str) -> Dict[str, Any]:
        """
        Get quotation for any supported doctype
        
        Args:
            doctype: Source doctype
            docname: Source document name
            
        Returns:
            Quotation data
        """
        try:
            mapper = self._get_mapper()
            quotation_request = mapper.map_to_quotation_request(doctype, docname)
            
            client = self._get_client()
            response = client.get_quotation(quotation_request)
            
            # Map to standard format
            standardized = mapper.map_from_quotation_response(response)
            
            # Cache quotation
            self._cache_quotation(doctype, docname, standardized)
            
            return standardized
            
        except Exception as e:
            frappe.log_error(
                f"Error getting ODDS quotation for {doctype} {docname}: {str(e)}",
                "ODDS Quotation Error"
            )
            raise
    
    def create_order(
        self, 
        doctype: str, 
        docname: str, 
        quotation_id: str = None,
        auto_get_quotation: bool = True
    ) -> Dict[str, Any]:
        """
        Create ODDS order from any supported doctype
        
        Args:
            doctype: Source doctype
            docname: Source document name
            quotation_id: Quotation ID (if None, will get new quotation)
            auto_get_quotation: If True and quotation_id is None, get quotation automatically
            
        Returns:
            Order data
        """
        try:
            client = self._get_client()
            mapper = self._get_mapper()
            provider = self._get_provider()
            
            # Get quotation if not provided
            quotation_data = None
            if not quotation_id:
                if auto_get_quotation:
                    quotation_response = self.get_quotation(doctype, docname)
                    quotation_id = quotation_response.get("quotation_id")
                    quotation_data = quotation_response
                    if not quotation_id:
                        raise ODDSException("Failed to get quotation ID from response")
                else:
                    raise ValueError("quotation_id is required when auto_get_quotation is False")
            else:
                # Get cached quotation data
                quotation_name = frappe.db.get_value("ODDS Quotation", {"quotation_id": quotation_id}, "name")
                if quotation_name:
                    quotation_doc = frappe.get_doc("ODDS Quotation", quotation_name)
                    import json
                    quotation_data = json.loads(quotation_doc.quotation_data) if quotation_doc.quotation_data else None
            
            # Verify quotation is still valid (if applicable)
            quotation = self._get_cached_quotation(quotation_id)
            if quotation and not self._is_quotation_valid(quotation):
                # Get new quotation
                quotation_response = self.get_quotation(doctype, docname)
                quotation_id = quotation_response.get("quotation_id")
                quotation_data = quotation_response
            
            # For providers that need full order request (not just quotation_id)
            order_request = None
            if provider.provider_code == "transportify":
                order_request = mapper.map_to_quotation_request(doctype, docname)
                if quotation_data and quotation_data.get("quote_data"):
                    pass
            elif provider.provider_code == "grabexpress":
                map_fn = getattr(mapper, "map_to_order_request", None)
                if map_fn:
                    order_request = map_fn(doctype, docname)

            # Place order
            if order_request:
                # For providers like Deliveree that need full order request
                order_response = client.place_order(quotation_id="", order_request=order_request)
            else:
                # For providers like Lalamove that use quotation_id
                order_response = client.place_order(quotation_id)
            
            # Map to standard format
            standardized = mapper.map_from_order_response(order_response)
            
            # Store order
            self._store_order(doctype, docname, quotation_id, standardized, provider.provider_code)
            
            return standardized
            
        except Exception as e:
            frappe.log_error(
                f"Error creating ODDS order for {doctype} {docname}: {str(e)}",
                "ODDS Order Creation Error"
            )
            raise
    
    def get_order_details(self, order_id: str) -> Dict[str, Any]:
        """Get order details"""
        client = self._get_client()
        mapper = self._get_mapper()
        response = client.get_order_details(order_id)
        return mapper.map_from_order_response(response)
    
    def sync_order_status(self, order_id: str) -> Dict[str, Any]:
        """Sync order status and update local records"""
        try:
            order_data = self.get_order_details(order_id)
            self._update_odds_order(order_id, order_data)
            self._update_source_document_status(order_id, order_data)
            return order_data
        except Exception as e:
            frappe.log_error(
                f"Error syncing ODDS order status {order_id}: {str(e)}",
                "ODDS Status Sync Error"
            )
            raise
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel order"""
        try:
            client = self._get_client()
            response = client.cancel_order(order_id)
            self.sync_order_status(order_id)
            return response
        except Exception as e:
            frappe.log_error(
                f"Error cancelling ODDS order {order_id}: {str(e)}",
                "ODDS Order Cancellation Error"
            )
            raise
    
    # Helper methods
    
    def _cache_quotation(self, doctype: str, docname: str, quotation_data: Dict[str, Any]):
        """Cache quotation in ODDS Quotation doctype"""
        try:
            quotation_id = quotation_data.get("quotation_id")
            if not quotation_id:
                return
            
            provider_code = self._get_provider().provider_code
            existing = frappe.db.exists("ODDS Quotation", {"quotation_id": quotation_id, "provider": provider_code})
            
            if existing:
                quotation = frappe.get_doc("ODDS Quotation", existing)
            else:
                quotation = frappe.new_doc("ODDS Quotation")
                quotation.quotation_id = quotation_id
                quotation.provider = self._get_provider().provider_code
            
            quotation.source_doctype = doctype
            quotation.source_docname = docname
            quotation.price = quotation_data.get("price", 0)
            quotation.currency = quotation_data.get("currency", "USD")
            quotation.expires_at = quotation_data.get("expires_at")
            quotation.valid = True
            quotation.quotation_data = frappe.as_json(quotation_data)
            
            quotation.save(ignore_permissions=True)
            frappe.db.commit()
            
        except Exception as e:
            frappe.log_error(f"Error caching quotation: {str(e)}", "ODDS Quotation Cache Error")
    
    def _get_cached_quotation(self, quotation_id: str) -> Optional[Dict[str, Any]]:
        """Get cached quotation"""
        try:
            quotation_name = frappe.db.get_value("ODDS Quotation", {"quotation_id": quotation_id}, "name")
            if not quotation_name:
                return None
            
            quotation = frappe.get_doc("ODDS Quotation", quotation_name)
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
            from datetime import datetime
            expiry_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            return datetime.now(expiry_time.tzinfo) < expiry_time
        except Exception:
            return False
    
    def _store_order(
        self, 
        doctype: str, 
        docname: str, 
        quotation_id: str, 
        order_data: Dict[str, Any],
        provider_code: str
    ):
        """Store order in ODDS Order doctype"""
        try:
            order_id = order_data.get("order_id")
            if not order_id:
                return
            
            # Use get_value with filters to find existing order
            existing = frappe.db.get_value("ODDS Order", {"order_id": order_id, "provider": provider_code}, "name")
            
            if existing:
                order = frappe.get_doc("ODDS Order", existing)
            else:
                order = frappe.new_doc("ODDS Order")
                order.order_id = order_id
                order.provider = provider_code
            
            order.quotation_id = quotation_id
            order.source_doctype = doctype
            order.source_docname = docname
            order.status = order_data.get("status", "PENDING")
            order.price = order_data.get("price", 0)
            order.currency = order_data.get("currency", "USD")
            order.order_data = frappe.as_json(order_data)
            
            order.save(ignore_permissions=True)
            frappe.db.commit()
            
            self._update_source_document_odds_order(doctype, docname, order.name)
            
        except Exception as e:
            frappe.log_error(f"Error storing ODDS order: {str(e)}", "ODDS Order Storage Error")
    
    def _update_odds_order(self, order_id: str, order_data: Dict[str, Any]):
        """Update ODDS Order record"""
        try:
            # Find order by order_id
            order_name = frappe.db.get_value("ODDS Order", {"order_id": order_id}, "name")
            if not order_name:
                return
            
            order = frappe.get_doc("ODDS Order", order_name)
            order.status = order_data.get("status", order.status)
            order.price = order_data.get("price", order.price)
            order.order_data = frappe.as_json(order_data)
            order.save(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"Error updating ODDS Order {order_id}: {str(e)}", "ODDS Order Update Error")
    
    def _update_source_document_odds_order(self, doctype: str, docname: str, odds_order_name: str):
        """Update source document with ODDS Order reference"""
        try:
            if frappe.db.exists(doctype, docname):
                frappe.db.set_value(
                    doctype,
                    docname,
                    "odds_order",
                    odds_order_name,
                    update_modified=False
                )
                frappe.db.commit()
        except Exception as e:
            frappe.log_error(
                f"Error updating source document {doctype} {docname}: {str(e)}",
                "ODDS Source Document Update Error"
            )
    
    def _update_source_document_status(self, order_id: str, order_data: Dict[str, Any]):
        """Update source document status based on order status"""
        try:
            order_name = frappe.db.get_value("ODDS Order", {"order_id": order_id}, "name")
            if not order_name:
                return
            
            order = frappe.get_doc("ODDS Order", order_name)
            if not order.source_doctype or not order.source_docname:
                return
            
            # Status update logic can be implemented per module
            pass
            
        except Exception as e:
            frappe.log_error(
                f"Error updating source document status: {str(e)}",
                "ODDS Status Update Error"
            )

