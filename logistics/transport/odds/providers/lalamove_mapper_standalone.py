# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Lalamove Mapper - Standalone Implementation

Self-contained Lalamove mapper for ODDS system.
No dependencies on old logistics/lalamove code.
"""

import frappe
from typing import Dict, Any, List, Optional
from frappe.utils import get_datetime
from ..base import ODDSMapper


class LalamoveMapperStandalone(ODDSMapper):
    """
    Maps data between Logistics modules and Lalamove API format
    Standalone implementation - no dependencies on old code
    """
    
    def __init__(self):
        super().__init__("lalamove")
    
    def map_to_quotation_request(self, doctype: str, docname: str) -> Dict[str, Any]:
        """
        Map source document to Lalamove quotation request
        
        Args:
            doctype: Source doctype
            docname: Source document name
            
        Returns:
            Lalamove quotation request dictionary
        """
        if doctype == "Transport Order":
            return self._map_transport_order_to_quotation(docname)
        elif doctype == "Transport Job":
            return self._map_transport_job_to_quotation(docname)
        elif doctype == "Transport Leg":
            return self._map_transport_leg_to_quotation(docname)
        elif doctype == "Warehouse Job":
            return self._map_warehouse_job_to_quotation(docname)
        elif doctype == "Air Shipment":
            return self._map_air_shipment_to_quotation(docname)
        elif doctype == "Air Booking":
            return self._map_air_booking_to_quotation(docname)
        elif doctype == "Sea Shipment":
            return self._map_sea_shipment_to_quotation(docname)
        elif doctype == "Sea Booking":
            return self._map_sea_booking_to_quotation(docname)
        else:
            raise ValueError(f"Unsupported doctype: {doctype}")
    
    def _map_transport_order_to_quotation(self, docname: str) -> Dict[str, Any]:
        """Map Transport Order to quotation request"""
        doc = frappe.get_doc("Transport Order", docname)
        
        legs = doc.get("legs") or []
        if not legs:
            raise ValueError("Transport Order must have at least one leg")
        
        first_leg = legs[0]
        stops = []
        
        # Pick-up stop
        if first_leg.get("pick_address"):
            pick_stop = self._create_stop_from_address(first_leg.pick_address)
            stops.append(pick_stop)
        else:
            raise ValueError("Pick address is required")
        
        # Drop-off stop
        if first_leg.get("drop_address"):
            drop_stop = self._create_stop_from_address(first_leg.drop_address)
            stops.append(drop_stop)
        else:
            raise ValueError("Drop address is required")
        
        # Additional stops from remaining legs
        for leg in legs[1:]:
            if leg.get("drop_address"):
                drop_stop = self._create_stop_from_address(leg.drop_address)
                stops.append(drop_stop)
        
        quotation_request = {
            "serviceType": self._map_vehicle_type_to_service_type(doc.vehicle_type),
            "stops": stops,
            "item": self._map_packages_to_item(doc.get("packages") or []),
        }
        
        # Add special requests
        special_requests = []
        if doc.get("hazardous"):
            special_requests.append("HAZMAT")
        if doc.get("reefer"):
            special_requests.append("REEFER")
        if special_requests:
            quotation_request["specialRequests"] = special_requests
        
        # Add scheduled time if available
        if doc.get("scheduled_date"):
            scheduled_at = get_datetime(f"{doc.scheduled_date} {doc.get('scheduled_time', '09:00:00')}")
            quotation_request["scheduleAt"] = scheduled_at.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        
        # Add contact information
        contact = self._get_contact_from_customer(doc.customer)
        if contact:
            quotation_request["contact"] = contact
        
        return quotation_request
    
    def _map_transport_job_to_quotation(self, docname: str) -> Dict[str, Any]:
        """Map Transport Job to quotation request"""
        doc = frappe.get_doc("Transport Job", docname)
        
        legs = doc.get("legs") or []
        if not legs:
            raise ValueError("Transport Job must have at least one leg")
        
        first_leg = legs[0]
        stops = []
        
        if first_leg.get("pick_address"):
            pick_stop = self._create_stop_from_address(first_leg.pick_address)
            stops.append(pick_stop)
        else:
            raise ValueError("Pick address is required")
        
        if first_leg.get("drop_address"):
            drop_stop = self._create_stop_from_address(first_leg.drop_address)
            stops.append(drop_stop)
        else:
            raise ValueError("Drop address is required")
        
        for leg in legs[1:]:
            if leg.get("drop_address"):
                drop_stop = self._create_stop_from_address(leg.drop_address)
                stops.append(drop_stop)
        
        quotation_request = {
            "serviceType": self._map_vehicle_type_to_service_type(doc.vehicle_type),
            "stops": stops,
            "item": self._map_packages_to_item(doc.get("packages") or []),
        }
        
        special_requests = []
        if doc.get("hazardous"):
            special_requests.append("HAZMAT")
        if doc.get("refrigeration"):
            special_requests.append("REEFER")
        if special_requests:
            quotation_request["specialRequests"] = special_requests
        
        contact = self._get_contact_from_customer(doc.customer)
        if contact:
            quotation_request["contact"] = contact
        
        return quotation_request
    
    def _map_transport_leg_to_quotation(self, docname: str) -> Dict[str, Any]:
        """Map Transport Leg to quotation request"""
        doc = frappe.get_doc("Transport Leg", docname)
        
        stops = []
        
        if doc.get("pick_address"):
            stops.append(self._create_stop_from_address(doc.pick_address))
        else:
            raise ValueError("Pick address is required")
        
        if doc.get("drop_address"):
            stops.append(self._create_stop_from_address(doc.drop_address))
        else:
            raise ValueError("Drop address is required")
        
        quotation_request = {
            "serviceType": self._map_vehicle_type_to_service_type(doc.vehicle_type),
            "stops": stops,
        }
        
        if doc.transport_job:
            job = frappe.get_doc("Transport Job", doc.transport_job)
            contact = self._get_contact_from_customer(job.customer)
            if contact:
                quotation_request["contact"] = contact
        
        return quotation_request
    
    def _map_warehouse_job_to_quotation(self, docname: str) -> Dict[str, Any]:
        """Map Warehouse Job to quotation request"""
        doc = frappe.get_doc("Warehouse Job", docname)
        
        stops = []
        
        warehouse_address = self._get_warehouse_address()
        if warehouse_address:
            stops.append(self._create_stop_from_address(warehouse_address))
        else:
            raise ValueError("Warehouse address not configured")
        
        delivery_address = doc.get("delivery_address") or self._get_customer_address(doc.customer)
        if delivery_address:
            stops.append(self._create_stop_from_address(delivery_address))
        else:
            raise ValueError("Delivery address is required")
        
        service_type = self._determine_service_type_from_items(doc.get("items") or [])
        
        quotation_request = {
            "serviceType": service_type,
            "stops": stops,
            "item": self._map_warehouse_items_to_item(doc.get("items") or []),
        }
        
        contact = self._get_contact_from_customer(doc.customer)
        if contact:
            quotation_request["contact"] = contact
        
        return quotation_request
    
    def _map_air_shipment_to_quotation(self, docname: str) -> Dict[str, Any]:
        """Map Air Shipment to quotation request"""
        doc = frappe.get_doc("Air Shipment", docname)
        
        stops = []
        
        airport_address = self._get_airport_address(doc.destination_port)
        if airport_address:
            stops.append(self._create_stop_from_address(airport_address))
        else:
            raise ValueError("Airport/CFS address not found")
        
        if doc.get("consignee_address"):
            stops.append(self._create_stop_from_address(doc.consignee_address))
        else:
            raise ValueError("Consignee address is required")
        
        service_type = self._determine_service_type_from_packages(doc.get("packages") or [])
        
        quotation_request = {
            "serviceType": service_type,
            "stops": stops,
            "item": self._map_packages_to_item(doc.get("packages") or []),
        }
        
        if doc.get("last_mile_delivery_date"):
            scheduled_at = get_datetime(doc.last_mile_delivery_date)
            quotation_request["scheduleAt"] = scheduled_at.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        elif doc.get("eta"):
            quotation_request["scheduleAt"] = get_datetime(doc.eta).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        
        if doc.consignee_contact:
            contact = self._get_contact_from_contact(doc.consignee_contact)
            if contact:
                quotation_request["contact"] = contact
        
        return quotation_request
    
    def _map_air_booking_to_quotation(self, docname: str) -> Dict[str, Any]:
        """Map Air Booking to quotation request"""
        return self._map_air_shipment_to_quotation(docname)
    
    def _map_sea_shipment_to_quotation(self, docname: str) -> Dict[str, Any]:
        """Map Sea Shipment to quotation request"""
        doc = frappe.get_doc("Sea Shipment", docname)
        
        stops = []
        
        port_address = self._get_port_address(doc.destination_port)
        if port_address:
            stops.append(self._create_stop_from_address(port_address))
        else:
            raise ValueError("Port/CFS address not found")
        
        if doc.get("consignee_address"):
            stops.append(self._create_stop_from_address(doc.consignee_address))
        else:
            raise ValueError("Consignee address is required")
        
        service_type = "TRUCK"  # Default for sea freight
        
        quotation_request = {
            "serviceType": service_type,
            "stops": stops,
            "item": self._map_packages_to_item(doc.get("packages") or []),
        }
        
        if doc.get("last_mile_delivery_date"):
            scheduled_at = get_datetime(doc.last_mile_delivery_date)
            quotation_request["scheduleAt"] = scheduled_at.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        elif doc.get("eta"):
            quotation_request["scheduleAt"] = get_datetime(doc.eta).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        
        if doc.consignee_contact:
            contact = self._get_contact_from_contact(doc.consignee_contact)
            if contact:
                quotation_request["contact"] = contact
        
        return quotation_request
    
    def _map_sea_booking_to_quotation(self, docname: str) -> Dict[str, Any]:
        """Map Sea Booking to quotation request"""
        return self._map_sea_shipment_to_quotation(docname)
    
    # Helper methods (inherit from base class where possible)
    
    def _map_vehicle_type_to_service_type(self, vehicle_type: str = None) -> str:
        """Map vehicle type to Lalamove service type"""
        if not vehicle_type:
            return "VAN"
        
        vehicle_type_lower = vehicle_type.lower()
        
        if "motorcycle" in vehicle_type_lower or "bike" in vehicle_type_lower:
            return "MOTORCYCLE"
        elif "van" in vehicle_type_lower:
            return "VAN"
        elif "truck" in vehicle_type_lower or "container" in vehicle_type_lower:
            return "TRUCK"
        else:
            return "VAN"
    
    def _map_packages_to_item(self, packages: List) -> Dict[str, Any]:
        """Map packages to Lalamove item format"""
        if not packages:
            return {
                "quantity": "1",
                "weight": "1",
                "handlingInstructions": ""
            }
        
        total_quantity = len(packages)
        total_weight = sum(float(pkg.get("weight") or 0) for pkg in packages)
        
        description = ""
        if packages and hasattr(packages[0], "description"):
            description = packages[0].description or ""
        
        return {
            "quantity": str(total_quantity),
            "weight": str(total_weight) if total_weight > 0 else "1",
            "handlingInstructions": description
        }
    
    def _map_warehouse_items_to_item(self, items: List) -> Dict[str, Any]:
        """Map warehouse items to Lalamove item format"""
        if not items:
            return {
                "quantity": "1",
                "weight": "1",
                "handlingInstructions": ""
            }
        
        total_quantity = sum(float(item.get("qty") or 0) for item in items)
        total_weight = sum(float(item.get("weight") or 0) for item in items)
        
        return {
            "quantity": str(int(total_quantity)) if total_quantity > 0 else "1",
            "weight": str(total_weight) if total_weight > 0 else "1",
            "handlingInstructions": ""
        }
    
    def _determine_service_type_from_items(self, items: List) -> str:
        """Determine service type from warehouse items"""
        total_weight = sum(float(item.get("weight") or 0) for item in items)
        
        if total_weight < 5:
            return "MOTORCYCLE"
        elif total_weight < 50:
            return "VAN"
        else:
            return "TRUCK"
    
    def _determine_service_type_from_packages(self, packages: List) -> str:
        """Determine service type from packages"""
        total_weight = sum(float(pkg.get("weight") or 0) for pkg in packages)
        
        if total_weight < 5:
            return "MOTORCYCLE"
        elif total_weight < 50:
            return "VAN"
        else:
            return "TRUCK"
    
    def _get_contact_from_customer(self, customer: str) -> Optional[Dict[str, str]]:
        """Get contact information from customer"""
        try:
            customer_doc = frappe.get_doc("Customer", customer)
            
            contacts = frappe.get_all(
                "Contact",
                filters={"link_doctype": "Customer", "link_name": customer},
                fields=["name", "mobile_no", "phone", "email_id"],
                limit=1
            )
            
            if contacts:
                contact = contacts[0]
                phone = contact.get("mobile_no") or contact.get("phone")
                if phone:
                    return {
                        "name": customer_doc.customer_name,
                        "phone": phone
                    }
            
            return {
                "name": customer_doc.customer_name,
                "phone": ""
            }
        except Exception:
            return None
    
    def _get_contact_from_contact(self, contact_name: str) -> Optional[Dict[str, str]]:
        """Get contact information from Contact doctype"""
        try:
            contact = frappe.get_doc("Contact", contact_name)
            phone = contact.mobile_no or contact.phone
            
            if phone:
                return {
                    "name": contact.full_name or contact.first_name or "",
                    "phone": phone
                }
        except Exception:
            pass
        
        return None
    
    def _get_warehouse_address(self) -> Optional[str]:
        """Get warehouse address from settings"""
        try:
            settings = frappe.get_single("Warehouse Settings")
            if hasattr(settings, "warehouse_contract_address") and settings.warehouse_contract_address:
                return settings.warehouse_contract_address
        except Exception:
            pass
        
        return None
    
    def _get_customer_address(self, customer: str) -> Optional[str]:
        """Get customer's default address"""
        addresses = frappe.get_all(
            "Dynamic Link",
            filters={"link_doctype": "Customer", "link_name": customer, "parenttype": "Address"},
            fields=["parent"],
            limit=1
        )
        
        if addresses:
            return addresses[0].parent
        
        return None
    
    def _get_airport_address(self, airport_code: str) -> Optional[str]:
        """Get airport address (placeholder)"""
        return None
    
    def _get_port_address(self, port_code: str) -> Optional[str]:
        """Get port address (placeholder)"""
        return None
    
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

