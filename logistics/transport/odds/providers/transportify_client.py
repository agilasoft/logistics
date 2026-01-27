# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Transportify (Deliveree) Client Implementation

Implements ODDS client interface for Transportify using Deliveree API.
API Documentation: https://developers.deliveree.com/
"""

import frappe
import requests
from typing import Dict, Any, Optional
from ..base import ODDSClient
from ..exceptions import (
    ODDSAPIException,
    ODDSAuthenticationException,
    ODDSQuotationExpiredException
)


class TransportifyClient(ODDSClient):
    """Transportify (Deliveree) client implementation"""
    
    def __init__(self, settings: Dict[str, Any]):
        """
        Initialize Transportify client
        
        Args:
            settings: Transportify settings dictionary with api_key, environment
        """
        super().__init__("transportify", settings)
        self.api_key = settings.get("api_key")
        self.environment = settings.get("environment", "sandbox")
        self.base_url = self._get_base_url(self.environment)
        
        if not self.api_key:
            raise ODDSAuthenticationException(
                "Transportify API key not configured",
                provider="transportify"
            )
    
    def _get_base_url(self, environment: str) -> str:
        """Get base URL based on environment"""
        if environment == "production":
            return "https://api.deliveree.com/public_api/v10"
        return "https://api.sandbox.deliveree.com/public_api/v10"
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        return {
            "Content-Type": "application/json",
            "Authorization": self.api_key,
            "Accept": "application/json"
        }
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Dict[str, Any] = None,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Deliveree API
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            ODDSAPIException: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
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
            except:
                response_data = {"raw_response": response.text}
            
            # Handle errors
            if not response.ok:
                error_message = self._extract_error_message(response_data)
                
                if response.status_code == 401:
                    raise ODDSAuthenticationException(
                        f"Authentication failed: {error_message}",
                        status_code=response.status_code,
                        response_data=response_data,
                        provider="transportify"
                    )
                elif response.status_code == 422:
                    # Check for quotation expired or invalid
                    if "quote" in error_message.lower() or "expired" in error_message.lower():
                        raise ODDSQuotationExpiredException(
                            f"Quotation expired or invalid: {error_message}"
                        )
                    raise ODDSAPIException(
                        f"Validation error: {error_message}",
                        status_code=response.status_code,
                        response_data=response_data,
                        provider="transportify"
                    )
                else:
                    raise ODDSAPIException(
                        f"API error: {error_message}",
                        status_code=response.status_code,
                        response_data=response_data,
                        provider="transportify"
                    )
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            frappe.log_error(f"Transportify API request failed: {str(e)}", "Transportify API Error")
            raise ODDSAPIException(f"Request failed: {str(e)}", provider="transportify")
        except (ODDSAPIException, ODDSAuthenticationException, ODDSQuotationExpiredException):
            raise
        except Exception as e:
            frappe.log_error(f"Unexpected error in Transportify API request: {str(e)}", "Transportify API Error")
            raise ODDSAPIException(f"Unexpected error: {str(e)}", provider="transportify")
    
    def _extract_error_message(self, response_data: Dict[str, Any]) -> str:
        """Extract error message from response"""
        if isinstance(response_data, dict):
            if "message" in response_data:
                return response_data["message"]
            if "error" in response_data:
                return response_data["error"]
            if "errors" in response_data:
                errors = response_data["errors"]
                if isinstance(errors, list) and errors:
                    return str(errors[0])
                elif isinstance(errors, dict):
                    return str(errors)
        return "Unknown error"
    
    def get_quotation(self, quotation_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get delivery quotation
        
        Args:
            quotation_request: Quotation request data
            
        Returns:
            Quotation response data
        """
        return self._make_request("POST", "/deliveries/get_quote", data=quotation_request)
    
    def get_quotation_details(self, quotation_id: str) -> Dict[str, Any]:
        """
        Get quotation details (not directly supported by Deliveree API)
        
        Note: Deliveree doesn't have a separate quotation details endpoint.
        This method returns the quotation data if available.
        """
        # Deliveree doesn't support getting quotation details separately
        # The quotation is embedded in the quote response
        raise ODDSAPIException(
            "Quotation details endpoint not supported by Transportify/Deliveree API",
            provider="transportify"
        )
    
    def place_order(self, quotation_id: str = None, order_request: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Place delivery order (create booking)
        
        Args:
            quotation_id: Not used by Deliveree (they use order_request directly)
            order_request: Order/booking request data
            
        Returns:
            Order response data
        """
        if not order_request:
            raise ODDSAPIException(
                "Order request data is required for Transportify",
                provider="transportify"
            )
        
        return self._make_request("POST", "/deliveries", data=order_request)
    
    def get_order_details(self, order_id: str) -> Dict[str, Any]:
        """
        Get order/booking details
        
        Args:
            order_id: Booking ID
            
        Returns:
            Order details
        """
        return self._make_request("GET", f"/deliveries/{order_id}")
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel order/booking
        
        Args:
            order_id: Booking ID
            
        Returns:
            Cancellation response
        """
        return self._make_request("DELETE", f"/deliveries/{order_id}")
    
    def get_driver_details(self, driver_id: str) -> Dict[str, Any]:
        """
        Get driver details
        
        Note: Deliveree API doesn't have a separate driver endpoint.
        Driver information is included in booking details.
        """
        # Driver details are included in booking details
        # This method can be used to get booking with driver info
        booking = self.get_order_details(driver_id)  # Using booking ID
        driver = booking.get("data", {}).get("driver", {})
        if driver:
            return {"data": driver}
        raise ODDSAPIException(
            "Driver details not available for this booking",
            provider="transportify"
        )

