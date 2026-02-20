# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Lalamove API v3 Client

Handles authentication, request signing, and API calls to Lalamove API.
"""

import frappe
import requests
import hmac
import hashlib
import base64
import json
from datetime import datetime
from typing import Dict, Any, Optional
from .exceptions import (
    LalamoveAPIException,
    LalamoveAuthenticationException,
    LalamoveQuotationExpiredException,
    LalamoveOrderException
)


class LalamoveAPIClient:
    """
    Lalamove API v3 Client
    
    Handles authentication, request signing, and API calls
    """
    
    def __init__(self, api_key: str = None, api_secret: str = None, environment: str = None):
        """
        Initialize Lalamove API client
        
        Args:
            api_key: Lalamove API key (if None, will fetch from settings)
            api_secret: Lalamove API secret (if None, will fetch from settings)
            environment: Environment (sandbox/production, if None, will fetch from settings)
        """
        if api_key is None or api_secret is None or environment is None:
            settings = self._get_settings()
            api_key = api_key or settings.get("api_key")
            api_secret = api_secret or settings.get("api_secret")
            environment = environment or settings.get("environment", "sandbox")
        
        if not api_key or not api_secret:
            raise LalamoveAuthenticationException("Lalamove API credentials not configured")
        
        self.api_key = api_key
        self.api_secret = api_secret
        self.environment = environment
        self.base_url = self._get_base_url(environment)
        self.timezone = "UTC"
    
    def _get_settings(self) -> Dict[str, Any]:
        """Get Lalamove settings"""
        try:
            from frappe.utils.password import get_decrypted_password
            
            settings = frappe.get_single("Lalamove Settings")
            if not settings.enabled:
                raise LalamoveAuthenticationException("Lalamove integration is not enabled")
            
            api_key = settings.api_key
            api_secret = get_decrypted_password(
                "Lalamove Settings",
                "Lalamove Settings",
                "api_secret",
                raise_exception=False
            )
            
            return {
                "api_key": api_key,
                "api_secret": api_secret,
                "environment": settings.environment or "sandbox",
                "market": settings.market
            }
        except Exception as e:
            frappe.log_error(f"Error getting Lalamove settings: {str(e)}", "Lalamove Settings Error")
            raise LalamoveAuthenticationException(f"Failed to get Lalamove settings: {str(e)}")
    
    def _get_base_url(self, environment: str) -> str:
        """Get base URL based on environment"""
        if environment == "production":
            return "https://rest.lalamove.com/v3"
        return "https://rest.sandbox.lalamove.com/v3"
    
    def _generate_signature(self, method: str, path: str, body: str, timestamp: str) -> str:
        """
        Generate HMAC signature for request authentication
        
        Args:
            method: HTTP method (GET, POST, PUT, etc.)
            path: API path (e.g., /v3/quotations)
            body: Request body as string
            timestamp: Request timestamp in ISO 8601 format
            
        Returns:
            Base64 encoded HMAC signature
        """
        # Create signature string
        signature_string = f"{timestamp}\r\n{method}\r\n{path}\r\n\r\n{body}"
        
        # Generate HMAC SHA256
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_string.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        # Base64 encode
        return base64.b64encode(signature).decode('utf-8')
    
    def _get_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """
        Get request headers with authentication
        
        Args:
            method: HTTP method
            path: API path
            body: Request body as string
            
        Returns:
            Dictionary of headers
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        signature = self._generate_signature(method, path, body, timestamp)
        
        return {
            "Content-Type": "application/json",
            "Authorization": f"hmac {self.api_key}:{timestamp}:{signature}",
            "X-LLM-Market": self._get_settings().get("market", "HK_HKG")
        }
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Dict[str, Any] = None,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Lalamove API
        
        Args:
            method: HTTP method
            endpoint: API endpoint (e.g., /quotations)
            data: Request body data
            params: Query parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            LalamoveAPIException: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        body = json.dumps(data) if data else ""
        headers = self._get_headers(method, endpoint, body)
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data if data else None,
                params=params,
                timeout=30
            )
            
            # Parse response
            try:
                response_data = response.json()
            except Exception:
                response_data = {"raw_response": response.text}
            
            # Handle errors
            if not response.ok:
                error_message = self._extract_error_message(response_data)
                
                if response.status_code == 401:
                    raise LalamoveAuthenticationException(
                        f"Authentication failed: {error_message}",
                        status_code=response.status_code,
                        response_data=response_data
                    )
                elif response.status_code == 422:
                    # Check for quotation expired
                    if "quotation" in error_message.lower() and "expired" in error_message.lower():
                        raise LalamoveQuotationExpiredException(
                            f"Quotation expired: {error_message}",
                            status_code=response.status_code,
                            response_data=response_data
                        )
                    raise LalamoveAPIException(
                        f"Validation error: {error_message}",
                        status_code=response.status_code,
                        response_data=response_data
                    )
                else:
                    raise LalamoveAPIException(
                        f"API error: {error_message}",
                        status_code=response.status_code,
                        response_data=response_data
                    )
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            frappe.log_error(f"Lalamove API request failed: {str(e)}", "Lalamove API Error")
            raise LalamoveAPIException(f"Request failed: {str(e)}")
        except (LalamoveAPIException, LalamoveAuthenticationException, LalamoveQuotationExpiredException):
            raise
        except Exception as e:
            frappe.log_error(f"Unexpected error in Lalamove API request: {str(e)}", "Lalamove API Error")
            raise LalamoveAPIException(f"Unexpected error: {str(e)}")
    
    def _extract_error_message(self, response_data: Dict[str, Any]) -> str:
        """Extract error message from response"""
        if isinstance(response_data, dict):
            if "errors" in response_data and isinstance(response_data["errors"], list):
                errors = response_data["errors"]
                if errors:
                    first_error = errors[0]
                    if isinstance(first_error, dict):
                        return first_error.get("message", first_error.get("detail", "Unknown error"))
            if "message" in response_data:
                return response_data["message"]
        return "Unknown error"
    
    # API Methods
    
    def get_quotation(self, quotation_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get delivery quotation
        
        Args:
            quotation_request: Quotation request data
            
        Returns:
            Quotation response data
        """
        return self._make_request("POST", "/quotations", data=quotation_request)
    
    def get_quotation_details(self, quotation_id: str) -> Dict[str, Any]:
        """
        Get quotation details
        
        Args:
            quotation_id: Quotation ID
            
        Returns:
            Quotation details
        """
        return self._make_request("GET", f"/quotations/{quotation_id}")
    
    def place_order(self, quotation_id: str, order_request: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Place delivery order
        
        Args:
            quotation_id: Quotation ID
            order_request: Additional order request data (optional)
            
        Returns:
            Order response data
        """
        data = {"quotationId": quotation_id}
        if order_request:
            data.update(order_request)
        
        return self._make_request("POST", "/orders", data=data)
    
    def get_order_details(self, order_id: str) -> Dict[str, Any]:
        """
        Get order details
        
        Args:
            order_id: Order ID
            
        Returns:
            Order details
        """
        return self._make_request("GET", f"/orders/{order_id}")
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel order
        
        Args:
            order_id: Order ID
            
        Returns:
            Cancellation response
        """
        return self._make_request("PUT", f"/orders/{order_id}/cancel")
    
    def get_driver_details(self, driver_id: str) -> Dict[str, Any]:
        """
        Get driver details
        
        Args:
            driver_id: Driver ID
            
        Returns:
            Driver details
        """
        return self._make_request("GET", f"/drivers/{driver_id}")
    
    def change_driver(self, order_id: str) -> Dict[str, Any]:
        """
        Request driver change
        
        Args:
            order_id: Order ID
            
        Returns:
            Response data
        """
        return self._make_request("PUT", f"/orders/{order_id}/drivers")
    
    def add_priority_fee(self, order_id: str) -> Dict[str, Any]:
        """
        Add priority fee to order
        
        Args:
            order_id: Order ID
            
        Returns:
            Response data
        """
        return self._make_request("PUT", f"/orders/{order_id}/priority")
    
    def edit_order(self, order_id: str, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Edit order
        
        Args:
            order_id: Order ID
            order_data: Order data to update
            
        Returns:
            Updated order data
        """
        return self._make_request("PUT", f"/orders/{order_id}", data=order_data)
    
    def get_city_info(self) -> Dict[str, Any]:
        """
        Get city information
        
        Returns:
            City information
        """
        return self._make_request("GET", "/cities")


