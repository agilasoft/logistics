# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Transportify (Deliveree) Mapper Implementation

Maps data between logistics modules and Deliveree API format.
API Documentation: https://developers.deliveree.com/
"""

import frappe
from typing import Dict, Any, List, Optional
from ..base import ODDSMapper
from frappe.utils import get_datetime


class TransportifyMapper(ODDSMapper):
    """Transportify (Deliveree) mapper implementation"""
    
    def __init__(self):
        super().__init__("transportify")
    
    def map_to_quotation_request(self, doctype: str, docname: str) -> Dict[str, Any]:
        """
        Map source document to Deliveree quotation request
        
        Deliveree quote request format:
        {
            "vehicle_type_id": integer,
            "pickup_location": {latitude, longitude},
            "dropoff_locations": [{latitude, longitude, note}],
            "time_type": "now" | "schedule",
            "pickup_time": "ISO8601" (if schedule),
            ...
        }
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
        
        # Pickup location
        if not first_leg.get("pick_address"):
            raise ValueError("Pick address is required")
        
        pickup_location = self._get_location_from_address(first_leg.pick_address)
        
        # Dropoff locations
        dropoff_locations = []
        if first_leg.get("drop_address"):
            dropoff = self._get_location_from_address(first_leg.drop_address)
            dropoff["note"] = first_leg.get("notes") or ""
            dropoff_locations.append(dropoff)
        
        # Additional dropoffs from remaining legs
        for leg in legs[1:]:
            if leg.get("drop_address"):
                dropoff = self._get_location_from_address(leg.drop_address)
                dropoff["note"] = leg.get("notes") or ""
                dropoff_locations.append(dropoff)
        
        if not dropoff_locations:
            raise ValueError("At least one drop address is required")
        
        # Vehicle type
        vehicle_type_id = self._map_vehicle_type_to_deliveree_id(doc.vehicle_type)
        
        # Build quotation request
        quotation_request = {
            "vehicle_type_id": vehicle_type_id,
            "pickup_location": pickup_location,
            "dropoff_locations": dropoff_locations,
            "time_type": "now"  # Default to immediate
        }
        
        # Scheduled time
        if doc.get("scheduled_date"):
            scheduled_at = get_datetime(f"{doc.scheduled_date} {doc.get('scheduled_time', '09:00:00')}")
            quotation_request["time_type"] = "schedule"
            quotation_request["pickup_time"] = scheduled_at.isoformat()
        
        # Package information
        packages = doc.get("packages") or []
        if packages:
            quotation_request["cargo"] = self._map_packages_to_cargo(packages)
        
        return quotation_request
    
    def _map_transport_job_to_quotation(self, docname: str) -> Dict[str, Any]:
        """Map Transport Job to quotation request"""
        doc = frappe.get_doc("Transport Job", docname)
        
        # Similar to Transport Order
        legs = doc.get("legs") or []
        if not legs:
            raise ValueError("Transport Job must have at least one leg")
        
        first_leg = legs[0]
        pickup_location = self._get_location_from_address(first_leg.pick_address)
        
        dropoff_locations = []
        for leg in legs:
            if leg.get("drop_address"):
                dropoff = self._get_location_from_address(leg.drop_address)
                dropoff["note"] = leg.get("notes") or ""
                dropoff_locations.append(dropoff)
        
        vehicle_type_id = self._map_vehicle_type_to_deliveree_id(doc.vehicle_type)
        
        quotation_request = {
            "vehicle_type_id": vehicle_type_id,
            "pickup_location": pickup_location,
            "dropoff_locations": dropoff_locations,
            "time_type": "now"
        }
        
        if doc.get("scheduled_date"):
            scheduled_at = get_datetime(f"{doc.scheduled_date} {doc.get('scheduled_time', '09:00:00')}")
            quotation_request["time_type"] = "schedule"
            quotation_request["pickup_time"] = scheduled_at.isoformat()
        
        return quotation_request
    
    def _map_transport_leg_to_quotation(self, docname: str) -> Dict[str, Any]:
        """Map Transport Leg to quotation request"""
        doc = frappe.get_doc("Transport Leg", docname)
        
        pickup_location = self._get_location_from_address(doc.pick_address)
        dropoff_location = self._get_location_from_address(doc.drop_address)
        dropoff_location["note"] = doc.get("notes") or ""
        
        vehicle_type_id = self._map_vehicle_type_to_deliveree_id(doc.vehicle_type)
        
        return {
            "vehicle_type_id": vehicle_type_id,
            "pickup_location": pickup_location,
            "dropoff_locations": [dropoff_location],
            "time_type": "now"
        }
    
    def _map_warehouse_job_to_quotation(self, docname: str) -> Dict[str, Any]:
        """Map Warehouse Job to quotation request"""
        doc = frappe.get_doc("Warehouse Job", docname)
        
        # Pickup from warehouse
        warehouse_address = self._get_warehouse_address()
        if not warehouse_address:
            raise ValueError("Warehouse address not configured")
        
        pickup_location = self._get_location_from_address(warehouse_address)
        
        # Delivery to customer
        delivery_address = doc.get("delivery_address") or self._get_customer_address(doc.customer)
        if not delivery_address:
            raise ValueError("Delivery address is required")
        
        dropoff_location = self._get_location_from_address(delivery_address)
        dropoff_location["note"] = doc.get("delivery_notes") or ""
        
        # Determine vehicle type from items
        vehicle_type_id = self._determine_vehicle_type_from_items(doc.get("items") or [])
        
        quotation_request = {
            "vehicle_type_id": vehicle_type_id,
            "pickup_location": pickup_location,
            "dropoff_locations": [dropoff_location],
            "time_type": "now"
        }
        
        # Add cargo if items available
        items = doc.get("items") or []
        if items:
            quotation_request["cargo"] = self._map_warehouse_items_to_cargo(items)
        
        return quotation_request
    
    def _map_air_shipment_to_quotation(self, docname: str) -> Dict[str, Any]:
        """Map Air Shipment to quotation request"""
        doc = frappe.get_doc("Air Shipment", docname)
        
        # Pickup from airport/CFS
        airport_address = self._get_airport_address(doc.destination_port)
        if not airport_address:
            raise ValueError("Airport/CFS address not found")
        
        pickup_location = self._get_location_from_address(airport_address)
        
        # Delivery to consignee
        if not doc.get("consignee_address"):
            raise ValueError("Consignee address is required")
        
        dropoff_location = self._get_location_from_address(doc.consignee_address)
        dropoff_location["note"] = doc.get("delivery_instructions") or ""
        
        vehicle_type_id = self._determine_vehicle_type_from_packages(doc.get("packages") or [])
        
        quotation_request = {
            "vehicle_type_id": vehicle_type_id,
            "pickup_location": pickup_location,
            "dropoff_locations": [dropoff_location],
            "time_type": "schedule"  # Usually scheduled for air freight
        }
        
        if doc.get("last_mile_delivery_date"):
            pickup_time = get_datetime(doc.last_mile_delivery_date)
            quotation_request["pickup_time"] = pickup_time.isoformat()
        elif doc.get("eta"):
            pickup_time = get_datetime(doc.eta)
            quotation_request["pickup_time"] = pickup_time.isoformat()
        
        return quotation_request
    
    def _map_air_booking_to_quotation(self, docname: str) -> Dict[str, Any]:
        """Map Air Booking to quotation request"""
        # Similar to Air Shipment
        return self._map_air_shipment_to_quotation(docname)
    
    def _map_sea_shipment_to_quotation(self, docname: str) -> Dict[str, Any]:
        """Map Sea Shipment to quotation request"""
        doc = frappe.get_doc("Sea Shipment", docname)
        
        # Pickup from port/CFS
        port_address = self._get_port_address(doc.destination_port)
        if not port_address:
            raise ValueError("Port/CFS address not found")
        
        pickup_location = self._get_location_from_address(port_address)
        
        # Delivery to consignee
        if not doc.get("consignee_address"):
            raise ValueError("Consignee address is required")
        
        dropoff_location = self._get_location_from_address(doc.consignee_address)
        dropoff_location["note"] = doc.get("delivery_instructions") or ""
        
        # For sea freight, usually use larger vehicle
        vehicle_type_id = 27  # Default to Closed Van
        
        quotation_request = {
            "vehicle_type_id": vehicle_type_id,
            "pickup_location": pickup_location,
            "dropoff_locations": [dropoff_location],
            "time_type": "schedule"
        }
        
        if doc.get("last_mile_delivery_date"):
            pickup_time = get_datetime(doc.last_mile_delivery_date)
            quotation_request["pickup_time"] = pickup_time.isoformat()
        elif doc.get("eta"):
            pickup_time = get_datetime(doc.eta)
            quotation_request["pickup_time"] = pickup_time.isoformat()
        
        return quotation_request
    
    def _map_sea_booking_to_quotation(self, docname: str) -> Dict[str, Any]:
        """Map Sea Booking to quotation request"""
        # Similar to Sea Shipment
        return self._map_sea_shipment_to_quotation(docname)
    
    # Helper methods
    
    def _get_location_from_address(self, address_name: str) -> Dict[str, float]:
        """Get location (lat/lng) from Address doctype"""
        address = frappe.get_doc("Address", address_name)
        coordinates = self._get_address_coordinates(address)
        
        return {
            "latitude": coordinates["lat"],
            "longitude": coordinates["lng"]
        }
    
    def _map_vehicle_type_to_deliveree_id(self, vehicle_type: str = None) -> int:
        """
        Map vehicle type to Deliveree vehicle type ID
        
        Common Deliveree vehicle type IDs (may vary by region):
        - Motorcycle: varies
        - Van/L300: 82
        - Closed Van: 27
        - Truck: varies
        
        Note: In production, this should fetch available vehicle types
        from the API or use a mapping table.
        """
        if not vehicle_type:
            return 27  # Default to Closed Van
        
        vehicle_type_lower = vehicle_type.lower()
        
        # These are example IDs - should be configured per region
        if "motorcycle" in vehicle_type_lower or "bike" in vehicle_type_lower:
            return 1  # Example ID
        elif "van" in vehicle_type_lower or "l300" in vehicle_type_lower:
            return 82
        elif "truck" in vehicle_type_lower or "container" in vehicle_type_lower:
            return 27  # Example ID
        else:
            return 27  # Default to Closed Van
    
    def _map_packages_to_cargo(self, packages: List) -> Dict[str, Any]:
        """Map packages to Deliveree cargo format"""
        if not packages:
            return {}
        
        # Aggregate package information
        total_weight = sum(float(pkg.get("weight") or 0) for pkg in packages)
        total_quantity = len(packages)
        
        # Get dimensions from first package
        first_pkg = packages[0]
        length = float(first_pkg.get("length") or 0)
        width = float(first_pkg.get("width") or 0)
        height = float(first_pkg.get("height") or 0)
        
        cargo = {
            "quantity": total_quantity,
            "weight": total_weight if total_weight > 0 else 1
        }
        
        if length > 0 and width > 0 and height > 0:
            cargo["length"] = length
            cargo["width"] = width
            cargo["height"] = height
        
        return cargo
    
    def _map_warehouse_items_to_cargo(self, items: List) -> Dict[str, Any]:
        """Map warehouse items to Deliveree cargo format"""
        if not items:
            return {}
        
        total_weight = sum(float(item.get("weight") or 0) for item in items)
        total_quantity = sum(float(item.get("qty") or 0) for item in items)
        
        return {
            "quantity": int(total_quantity) if total_quantity > 0 else 1,
            "weight": total_weight if total_weight > 0 else 1
        }
    
    def _determine_vehicle_type_from_items(self, items: List) -> int:
        """Determine vehicle type from warehouse items"""
        total_weight = sum(float(item.get("weight") or 0) for item in items)
        
        if total_weight < 5:
            return 1  # Motorcycle
        elif total_weight < 50:
            return 82  # Van
        else:
            return 27  # Closed Van
    
    def _determine_vehicle_type_from_packages(self, packages: List) -> int:
        """Determine vehicle type from packages"""
        total_weight = sum(float(pkg.get("weight") or 0) for pkg in packages)
        
        if total_weight < 5:
            return 1  # Motorcycle
        elif total_weight < 50:
            return 82  # Van
        else:
            return 27  # Closed Van
    
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
        # This would typically look up airport address from a master data table
        return None
    
    def _get_port_address(self, port_code: str) -> Optional[str]:
        """Get port address (placeholder)"""
        # This would typically look up port address from a master data table
        return None
    
    def map_from_quotation_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map Deliveree quotation response to standard format
        
        Deliveree quote response format:
        {
            "data": {
                "price": ...,
                "currency": ...,
                "vehicle_type_name": ...,
                "distance": ...,
                ...
            }
        }
        
        Note: Deliveree doesn't return a quotation ID. We'll use a generated ID
        or the quote data hash as the quotation identifier.
        """
        data = response.get("data", {})
        
        # Generate a quotation ID from quote data (since Deliveree doesn't provide one)
        import hashlib
        import json
        quote_hash = hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()[:12]
        quotation_id = f"TFY-{quote_hash}"
        
        return {
            "quotation_id": quotation_id,
            "price": float(data.get("price", 0)),
            "currency": data.get("currency", "IDR"),
            "expires_at": None,  # Deliveree doesn't provide expiration
            "service_type": data.get("vehicle_type_name", ""),
            "distance": data.get("distance", 0),
            "price_breakdown": {
                "total": data.get("price", 0),
                "base": data.get("base_price", 0),
                "distance": data.get("distance_price", 0)
            },
            "quote_data": data,  # Store original quote data for order creation
            "raw_response": response
        }
    
    def map_from_order_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map Deliveree booking response to standard format
        
        Deliveree booking statuses:
        - locating_driver
        - driver_accept_booking
        - delivery_in_progress
        - delivery_complete
        - canceled
        - locating_driver_timeout
        """
        data = response.get("data", {})
        
        # Map Deliveree status to standard status
        deliveree_status = data.get("status", "")
        standard_status = self._map_deliveree_status(deliveree_status)
        
        # Extract driver information
        driver = data.get("driver", {})
        driver_info = {}
        if driver:
            driver_info = {
                "name": driver.get("name", ""),
                "phone": driver.get("phone", ""),
                "photo": driver.get("photo", "")
            }
        
        # Extract vehicle information
        vehicle = data.get("vehicle", {})
        vehicle_info = {}
        if vehicle:
            vehicle_info = {
                "type": vehicle.get("name", ""),
                "vehicleNumber": vehicle.get("plate_number", "")
            }
        
        return {
            "order_id": str(data.get("id", "")),
            "status": standard_status,
            "price": float(data.get("price", 0)),
            "currency": data.get("currency", "IDR"),
            "distance": data.get("distance", 0),
            "driver": driver_info,
            "vehicle": vehicle_info,
            "scheduled_at": data.get("pickup_time"),
            "completed_at": data.get("completed_at"),
            "raw_response": response
        }
    
    def _map_deliveree_status(self, deliveree_status: str) -> str:
        """Map Deliveree status to standard ODDS status"""
        status_mapping = {
            "locating_driver": "ASSIGNING_DRIVER",
            "driver_accept_booking": "ASSIGNING_DRIVER",
            "delivery_in_progress": "ON_GOING",
            "delivery_complete": "COMPLETED",
            "canceled": "CANCELLED",
            "locating_driver_timeout": "EXPIRED"
        }
        
        return status_mapping.get(deliveree_status, "PENDING")

