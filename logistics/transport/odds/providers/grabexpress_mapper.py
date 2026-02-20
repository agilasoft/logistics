# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
GrabExpress Mapper

Maps data between Logistics modules and GrabExpress API format.
API reference: https://developer-beta.stg-myteksi.com/docs/grab-express/#grabexpress
"""

import frappe
import uuid
from typing import Dict, Any, List, Optional
from frappe.utils import get_datetime
from ..base import ODDSMapper


class GrabExpressMapper(ODDSMapper):
    """Maps data between Logistics modules and GrabExpress API format"""

    def __init__(self):
        super().__init__("grabexpress")

    def map_to_quotation_request(self, doctype: str, docname: str) -> Dict[str, Any]:
        """Map source document to GrabExpress quotation request (GET quotes)"""
        base = self._build_base_request(doctype, docname)
        return {
            "serviceType": base.get("serviceType", "INSTANT"),
            "vehicleType": base.get("vehicleType", "BIKE"),
            "codType": "REGULAR",
            "packages": base["packages"],
            "origin": base["origin"],
            "destination": base["destination"],
        }

    def map_to_order_request(self, doctype: str, docname: str) -> Dict[str, Any]:
        """Map source document to full GrabExpress create delivery request"""
        base = self._build_base_request(doctype, docname)
        return {
            "merchantOrderID": f"GE-{doctype}-{docname}-{uuid.uuid4().hex[:8]}",
            "serviceType": base.get("serviceType", "INSTANT"),
            "vehicleType": base.get("vehicleType", "BIKE"),
            "paymentMethod": "CASHLESS",
            "packages": base["packages"],
            "origin": base["origin"],
            "destination": base["destination"],
            "sender": base.get("sender", {"firstName": "Sender", "email": "s@x.com", "phone": "0000000000", "smsEnabled": False}),
            "recipient": base.get("recipient", {"firstName": "Recipient", "email": "r@x.com", "phone": "0000000000", "smsEnabled": False}),
            "schedule": base.get("schedule"),
        }

    def _build_base_request(self, doctype: str, docname: str) -> Dict[str, Any]:
        """Build base request used for both quotes and create delivery"""
        if doctype == "Transport Order":
            return self._map_transport_order(docname)
        elif doctype == "Transport Job":
            return self._map_transport_job(docname)
        elif doctype == "Transport Leg":
            return self._map_transport_leg(docname)
        elif doctype == "Warehouse Job":
            return self._map_warehouse_job(docname)
        elif doctype in ("Air Shipment", "Air Booking", "Sea Shipment", "Sea Booking"):
            return self._map_freight_doc(doctype, docname)
        else:
            raise ValueError(f"Unsupported doctype: {doctype}")

    def _map_transport_order(self, docname: str) -> Dict[str, Any]:
        doc = frappe.get_doc("Transport Order", docname)
        legs = doc.get("legs") or []
        if not legs:
            raise ValueError("Transport Order must have at least one leg")

        first = legs[0]
        origin = self._address_to_grab_location(first.get("pick_address"))
        destination = self._address_to_grab_location(first.get("drop_address"))
        if not origin or not destination:
            raise ValueError("Pick and drop addresses with coordinates are required")

        return {
            "packages": self._map_packages(doc.get("packages") or []),
            "origin": origin,
            "destination": destination,
            "serviceType": "INSTANT",
            "vehicleType": self._map_vehicle_type(doc.get("vehicle_type")),
            "sender": self._get_sender(doc.customer, first.get("pick_address")),
            "recipient": self._get_recipient(doc.customer, first.get("drop_address")),
            "schedule": self._get_schedule(doc),
        }

    def _map_transport_job(self, docname: str) -> Dict[str, Any]:
        doc = frappe.get_doc("Transport Job", docname)
        legs = doc.get("legs") or []
        if not legs:
            raise ValueError("Transport Job must have at least one leg")

        first = legs[0]
        origin = self._address_to_grab_location(first.get("pick_address"))
        destination = self._address_to_grab_location(first.get("drop_address"))
        if not origin or not destination:
            raise ValueError("Pick and drop addresses with coordinates are required")

        return {
            "packages": self._map_packages(doc.get("packages") or []),
            "origin": origin,
            "destination": destination,
            "serviceType": "INSTANT",
            "vehicleType": self._map_vehicle_type(doc.get("vehicle_type")),
            "sender": self._get_sender(doc.customer, first.get("pick_address")),
            "recipient": self._get_recipient(doc.customer, first.get("drop_address")),
            "schedule": self._get_schedule(doc),
        }

    def _map_transport_leg(self, docname: str) -> Dict[str, Any]:
        doc = frappe.get_doc("Transport Leg", docname)
        origin = self._address_to_grab_location(doc.get("pick_address"))
        destination = self._address_to_grab_location(doc.get("drop_address"))
        if not origin or not destination:
            raise ValueError("Pick and drop addresses with coordinates are required")

        job = frappe.get_doc("Transport Job", doc.transport_job) if doc.transport_job else None
        customer = job.customer if job else None

        return {
            "packages": self._map_packages(doc.get("packages") or job.get("packages") or []),
            "origin": origin,
            "destination": destination,
            "serviceType": "INSTANT",
            "vehicleType": self._map_vehicle_type(job.get("vehicle_type") if job else None),
            "sender": self._get_sender(customer, doc.get("pick_address")),
            "recipient": self._get_recipient(customer, doc.get("drop_address")),
            "schedule": self._get_schedule(doc) or (self._get_schedule(job) if job else None),
        }

    def _map_warehouse_job(self, docname: str) -> Dict[str, Any]:
        doc = frappe.get_doc("Warehouse Job", docname)
        origin = self._get_warehouse_address()
        destination = self._get_customer_address(doc.customer)
        if not origin or not destination:
            raise ValueError("Warehouse and customer addresses with coordinates are required")

        origin_loc = self._address_to_grab_location(origin)
        dest_loc = self._address_to_grab_location(destination)
        if not origin_loc or not dest_loc:
            raise ValueError("Addresses must have coordinates")

        return {
            "packages": self._map_warehouse_items(doc.get("items") or []),
            "origin": origin_loc,
            "destination": dest_loc,
            "serviceType": "INSTANT",
            "vehicleType": "VAN",
            "sender": self._get_sender_from_address(origin),
            "recipient": self._get_recipient_from_customer(doc.customer, destination),
            "schedule": None,
        }

    def _map_freight_doc(self, doctype: str, docname: str) -> Dict[str, Any]:
        if doctype == "Air Booking":
            doc = frappe.get_doc("Air Booking", docname)
        elif doctype == "Air Shipment":
            doc = frappe.get_doc("Air Shipment", docname)
        elif doctype == "Sea Booking":
            doc = frappe.get_doc("Sea Booking", docname)
        else:
            doc = frappe.get_doc("Sea Shipment", docname)

        origin = self._address_to_grab_location(
            doc.get("shipper_address") or doc.get("origin_address")
        )
        destination = self._address_to_grab_location(
            doc.get("consignee_address") or doc.get("destination_address")
        )
        if not origin or not destination:
            raise ValueError("Shipper and consignee addresses with coordinates are required")

        return {
            "packages": self._map_packages(doc.get("packages") or []),
            "origin": origin,
            "destination": destination,
            "serviceType": "INSTANT",
            "vehicleType": "VAN",
            "sender": self._get_sender_from_contact(doc.get("shipper_contact"), doc.get("shipper")),
            "recipient": self._get_recipient_from_contact(
                doc.get("consignee_contact"), doc.get("consignee")
            ),
            "schedule": self._get_schedule_from_freight(doc),
        }

    def _address_to_grab_location(self, address_name: str) -> Optional[Dict[str, Any]]:
        """Convert Address to GrabExpress origin/destination format"""
        if not address_name:
            return None
        try:
            address = frappe.get_doc("Address", address_name)
            coords = self._get_address_coordinates(address)
            address_str = self._format_address_string(address)
            return {
                "address": address_str,
                "coordinates": {
                    "latitude": coords["lat"],
                    "longitude": coords["lng"],
                },
            }
        except Exception:
            return None

    def _map_packages(self, packages: List) -> List[Dict[str, Any]]:
        """Map packages to GrabExpress format (dimensions in cm, weight in grams)"""
        if not packages:
            return [{
                "name": "Package",
                "description": "Delivery",
                "quantity": 1,
                "price": 0,
                "dimensions": {"height": 10, "width": 10, "depth": 10, "weight": 1000},
            }]

        result = []
        for pkg in packages:
            w = float(pkg.get("weight") or 1)
            h = float(pkg.get("height") or 10)
            wd = float(pkg.get("width") or 10)
            d = float(pkg.get("depth") or pkg.get("length") or 10)
            result.append({
                "name": str(pkg.get("description") or pkg.get("item") or "Package")[:500],
                "description": str(pkg.get("description") or "")[:500],
                "quantity": int(float(pkg.get("quantity") or 1)),
                "price": float(pkg.get("goods_value") or 0),
                "dimensions": {
                    "height": int(h),
                    "width": int(wd),
                    "depth": int(d),
                    "weight": int(w * 1000) if w < 100 else int(w),  # assume kg if small
                },
            })
        return result

    def _map_warehouse_items(self, items: List) -> List[Dict[str, Any]]:
        if not items:
            return [{
                "name": "Item",
                "description": "Warehouse delivery",
                "quantity": 1,
                "price": 0,
                "dimensions": {"height": 10, "width": 10, "depth": 10, "weight": 1000},
            }]
        total_qty = sum(float(i.get("quantity") or 0) for i in items)
        total_w = sum(float(i.get("weight") or 0) for i in items)
        return [{
            "name": "Warehouse items",
            "description": "Delivery",
            "quantity": int(total_qty) if total_qty > 0 else 1,
            "price": 0,
            "dimensions": {"height": 10, "width": 10, "depth": 10, "weight": int(total_w * 1000) if total_w > 0 else 1000},
        }]

    def _map_vehicle_type(self, vehicle_type: str = None) -> str:
        """Map to GrabExpress vehicleType: BIKE, CAR, VAN, TRUCK, etc."""
        if not vehicle_type:
            return "BIKE"
        v = str(vehicle_type).upper()
        if "BIKE" in v or "MOTOR" in v:
            return "BIKE"
        if "CAR" in v:
            return "CAR"
        if "VAN" in v:
            return "VAN"
        if "TRUCK" in v:
            return "TRUCK"
        return "VAN"

    def _get_sender(self, customer: str, address_name: str) -> Dict[str, Any]:
        contact = self._get_contact_from_customer(customer)
        addr = self._get_contact_from_address(address_name) if address_name else None
        name = (contact or {}).get("name", "Sender")
        phone = (contact or {}).get("phone") or (addr or {}).get("phone", "")
        email = (contact or {}).get("email") or (addr or {}).get("email", "sender@example.com")
        return {
            "firstName": name[:50],
            "email": email or "sender@example.com",
            "phone": str(phone).replace("+", "").replace(" ", "")[:25] if phone else "0000000000",
            "smsEnabled": False,
        }

    def _get_recipient(self, customer: str, address_name: str) -> Dict[str, Any]:
        return self._get_sender(customer, address_name)

    def _get_sender_from_address(self, address_name: str) -> Dict[str, Any]:
        c = self._get_contact_from_address(address_name)
        return {
            "firstName": (c or {}).get("name", "Sender")[:50],
            "email": (c or {}).get("email", "sender@example.com"),
            "phone": (c or {}).get("phone", "0000000000")[:25],
            "smsEnabled": False,
        }

    def _get_recipient_from_customer(self, customer: str, address_name: str) -> Dict[str, Any]:
        c = self._get_contact_from_customer(customer) or self._get_contact_from_address(address_name)
        return {
            "firstName": (c or {}).get("name", "Recipient")[:50],
            "email": (c or {}).get("email", "recipient@example.com"),
            "phone": (c or {}).get("phone", "0000000000")[:25],
            "smsEnabled": False,
        }

    def _get_sender_from_contact(self, contact_name: str, party_name: str) -> Dict[str, Any]:
        c = self._get_contact_from_contact(contact_name) if contact_name else None
        if not c and party_name:
            try:
                party = frappe.get_doc("Shipper", party_name)
                c = {"name": party.shipper_name, "phone": "", "email": ""}
            except Exception:
                pass
        return {
            "firstName": (c or {}).get("name", "Sender")[:50],
            "email": (c or {}).get("email", "sender@example.com"),
            "phone": (c or {}).get("phone", "0000000000")[:25],
            "smsEnabled": False,
        }

    def _get_recipient_from_contact(self, contact_name: str, party_name: str) -> Dict[str, Any]:
        c = self._get_contact_from_contact(contact_name) if contact_name else None
        if not c and party_name:
            try:
                party = frappe.get_doc("Consignee", party_name)
                c = {"name": party.consignee_name, "phone": "", "email": ""}
            except Exception:
                pass
        return {
            "firstName": (c or {}).get("name", "Recipient")[:50],
            "email": (c or {}).get("email", "recipient@example.com"),
            "phone": (c or {}).get("phone", "0000000000")[:25],
            "smsEnabled": False,
        }

    def _get_schedule(self, doc) -> Optional[Dict[str, str]]:
        if not doc:
            return None
        dt = doc.get("scheduled_date") or doc.get("booking_date")
        if not dt:
            return None
        tm = doc.get("scheduled_time") or "09:00:00"
        from_str = f"{dt}T{tm}"
        try:
            from_dt = get_datetime(from_str)
            to_dt = from_dt + __import__("datetime").timedelta(hours=1)
            return {
                "pickupTimeFrom": from_dt.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "pickupTimeTo": to_dt.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }
        except Exception:
            return None

    def _get_schedule_from_freight(self, doc) -> Optional[Dict[str, str]]:
        dt = doc.get("eta") or doc.get("etd")
        if not dt:
            return None
        try:
            from_dt = get_datetime(dt)
            to_dt = from_dt + __import__("datetime").timedelta(hours=1)
            return {
                "pickupTimeFrom": from_dt.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "pickupTimeTo": to_dt.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }
        except Exception:
            return None

    def _get_contact_from_customer(self, customer: str) -> Optional[Dict]:
        try:
            contacts = frappe.get_all(
                "Contact",
                filters={"link_doctype": "Customer", "link_name": customer},
                fields=["name", "mobile_no", "phone", "email_id"],
                limit=1,
            )
            if contacts:
                c = frappe.get_doc("Contact", contacts[0].name)
                return {
                    "name": c.full_name or c.first_name or "",
                    "phone": c.mobile_no or c.phone or "",
                    "email": c.email_id or "",
                }
        except Exception:
            pass
        return None

    def _get_contact_from_address(self, address_name: str) -> Optional[Dict]:
        try:
            links = frappe.get_all(
                "Dynamic Link",
                filters={"parenttype": "Address", "parent": address_name},
                fields=["link_doctype", "link_name"],
            )
            for link in links:
                if link.link_doctype == "Contact":
                    c = frappe.get_doc("Contact", link.link_name)
                    return {
                        "name": c.full_name or c.first_name or "",
                        "phone": c.mobile_no or c.phone or "",
                        "email": c.email_id or "",
                    }
        except Exception:
            pass
        return None

    def _get_contact_from_contact(self, contact_name: str) -> Optional[Dict]:
        try:
            c = frappe.get_doc("Contact", contact_name)
            return {
                "name": c.full_name or c.first_name or "",
                "phone": c.mobile_no or c.phone or "",
                "email": c.email_id or "",
            }
        except Exception:
            return None

    def _get_warehouse_address(self) -> Optional[str]:
        try:
            s = frappe.get_single("Warehouse Settings")
            return getattr(s, "warehouse_contract_address", None)
        except Exception:
            return None

    def _get_customer_address(self, customer: str) -> Optional[str]:
        links = frappe.get_all(
            "Dynamic Link",
            filters={"link_doctype": "Customer", "link_name": customer, "parenttype": "Address"},
            fields=["parent"],
            limit=1,
        )
        return links[0].parent if links else None

    def map_from_quotation_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Map GrabExpress quotes response to standard format"""
        quotes = response.get("quotes", [])
        if not quotes:
            return {
                "quotation_id": None,
                "price": 0,
                "currency": "SGD",
                "expires_at": None,
                "quotes": [],
                "raw_response": response,
            }

        best = quotes[0]
        for q in quotes[1:]:
            if float(q.get("amount", 0)) < float(best.get("amount", 0)):
                best = q

        currency = best.get("currency", {})
        return {
            "quotation_id": str(uuid.uuid4()),
            "price": float(best.get("amount", 0)),
            "currency": currency.get("code", "SGD"),
            "expires_at": None,
            "quotes": quotes,
            "service_type": best.get("service", {}).get("type"),
            "distance": best.get("distance", 0),
            "raw_response": response,
        }

    def map_from_order_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Map GrabExpress delivery response to standard format"""
        quote = response.get("quote", {})
        currency = quote.get("currency", {})
        return {
            "order_id": response.get("deliveryID"),
            "status": response.get("status", "PENDING"),
            "price": float(quote.get("amount", 0)),
            "currency": currency.get("code", "SGD"),
            "tracking_url": response.get("trackingURL", ""),
            "courier": response.get("courier"),
            "timeline": response.get("timeline"),
            "raw_response": response,
        }
