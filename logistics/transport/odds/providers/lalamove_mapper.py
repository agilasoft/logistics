# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Lalamove Mapper Adapter

Adapts the existing Lalamove mapper to the ODDS interface.
"""

from typing import Dict, Any
from ..base import ODDSMapper
from logistics.lalamove.mapper import LalamoveMapper as OriginalLalamoveMapper


class LalamoveMapper(ODDSMapper):
    """Lalamove mapper adapter for ODDS"""
    
    def __init__(self):
        super().__init__("lalamove")
        self._mapper = OriginalLalamoveMapper()
    
    def map_to_quotation_request(self, doctype: str, docname: str) -> Dict[str, Any]:
        """Map source document to Lalamove quotation request"""
        return self._mapper.map_to_quotation_request(doctype, docname)
    
    def map_from_quotation_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map Lalamove quotation response to standard format
        
        Lalamove response format:
        {
            "data": {
                "quotationId": "...",
                "priceBreakdown": {...},
                "expiresAt": "...",
                ...
            }
        }
        """
        data = response.get("data", {})
        
        return {
            "quotation_id": data.get("quotationId"),
            "price": data.get("priceBreakdown", {}).get("total", 0),
            "currency": data.get("priceBreakdown", {}).get("currency", "HKD"),
            "expires_at": data.get("expiresAt"),
            "service_type": data.get("serviceType"),
            "distance": data.get("distance", 0),
            "price_breakdown": data.get("priceBreakdown", {}),
            "stops": data.get("stops", []),
            "item": data.get("item", {}),
            "raw_response": response
        }
    
    def map_from_order_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map Lalamove order response to standard format
        
        Lalamove response format:
        {
            "data": {
                "orderId": "...",
                "status": "...",
                "price": ...,
                ...
            }
        }
        """
        data = response.get("data", {})
        
        return {
            "order_id": data.get("orderId"),
            "status": data.get("status", "PENDING"),
            "price": data.get("price", 0),
            "currency": data.get("currency", "HKD"),
            "distance": data.get("distance", 0),
            "driver": data.get("driver", {}),
            "vehicle": data.get("vehicle", {}),
            "scheduled_at": data.get("scheduleAt"),
            "completed_at": data.get("completedAt"),
            "raw_response": response
        }

