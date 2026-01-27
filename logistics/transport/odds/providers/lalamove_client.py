# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Lalamove Client Adapter

Adapts the existing Lalamove client to the ODDS interface.
"""

from typing import Dict, Any
from ..base import ODDSClient
from logistics.lalamove.client import LalamoveAPIClient
from ..exceptions import (
    ODDSAPIException,
    ODDSAuthenticationException,
    ODDSQuotationExpiredException
)


class LalamoveClient(ODDSClient):
    """Lalamove client adapter for ODDS"""
    
    def __init__(self, settings: Dict[str, Any]):
        """
        Initialize Lalamove client
        
        Args:
            settings: Lalamove settings dictionary
        """
        super().__init__("lalamove", settings)
        self._client = LalamoveAPIClient(
            api_key=settings.get("api_key"),
            api_secret=settings.get("api_secret"),
            environment=settings.get("environment", "sandbox")
        )
    
    def get_quotation(self, quotation_request: Dict[str, Any]) -> Dict[str, Any]:
        """Get delivery quotation"""
        try:
            return self._client.get_quotation(quotation_request)
        except Exception as e:
            self._handle_exception(e)
    
    def get_quotation_details(self, quotation_id: str) -> Dict[str, Any]:
        """Get quotation details"""
        try:
            return self._client.get_quotation_details(quotation_id)
        except Exception as e:
            self._handle_exception(e)
    
    def place_order(self, quotation_id: str, order_request: Dict[str, Any] = None) -> Dict[str, Any]:
        """Place delivery order"""
        try:
            return self._client.place_order(quotation_id, order_request)
        except Exception as e:
            self._handle_exception(e)
    
    def get_order_details(self, order_id: str) -> Dict[str, Any]:
        """Get order details"""
        try:
            return self._client.get_order_details(order_id)
        except Exception as e:
            self._handle_exception(e)
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel order"""
        try:
            return self._client.cancel_order(order_id)
        except Exception as e:
            self._handle_exception(e)
    
    def get_driver_details(self, driver_id: str) -> Dict[str, Any]:
        """Get driver details"""
        try:
            return self._client.get_driver_details(driver_id)
        except Exception as e:
            self._handle_exception(e)
    
    def _handle_exception(self, exception: Exception):
        """Convert Lalamove exceptions to ODDS exceptions"""
        from logistics.lalamove.exceptions import (
            LalamoveAPIException,
            LalamoveAuthenticationException,
            LalamoveQuotationExpiredException
        )
        
        if isinstance(exception, LalamoveAuthenticationException):
            raise ODDSAuthenticationException(
                str(exception),
                status_code=getattr(exception, 'status_code', None),
                response_data=getattr(exception, 'response_data', None),
                provider="lalamove"
            )
        elif isinstance(exception, LalamoveQuotationExpiredException):
            raise ODDSQuotationExpiredException(str(exception))
        elif isinstance(exception, LalamoveAPIException):
            raise ODDSAPIException(
                str(exception),
                status_code=getattr(exception, 'status_code', None),
                response_data=getattr(exception, 'response_data', None),
                provider="lalamove"
            )
        else:
            raise ODDSAPIException(str(exception), provider="lalamove")

