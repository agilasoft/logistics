# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class LalamoveOrder(Document):
    def validate(self):
        """Validate Lalamove Order"""
        # Ensure lalamove_order_id is unique
        if self.lalamove_order_id:
            existing = frappe.db.exists(
                "Lalamove Order",
                {
                    "lalamove_order_id": self.lalamove_order_id,
                    "name": ["!=", self.name]
                }
            )
            if existing:
                frappe.throw(f"Lalamove Order ID {self.lalamove_order_id} already exists")
        
        # Auto-populate module-specific links based on source_doctype
        self._populate_module_links()
    
    def _populate_module_links(self):
        """Populate module-specific link fields based on source_doctype"""
        if not self.source_doctype or not self.source_docname:
            return
        
        # Clear all module links first
        self.transport_order = None
        self.transport_job = None
        self.transport_leg = None
        self.warehouse_job = None
        self.air_shipment = None
        self.air_booking = None
        self.sea_shipment = None
        self.sea_booking = None
        
        # Set appropriate link based on source_doctype
        if self.source_doctype == "Transport Order":
            self.transport_order = self.source_docname
        elif self.source_doctype == "Transport Job":
            self.transport_job = self.source_docname
        elif self.source_doctype == "Transport Leg":
            self.transport_leg = self.source_docname
        elif self.source_doctype == "Warehouse Job":
            self.warehouse_job = self.source_docname
        elif self.source_doctype == "Air Shipment":
            self.air_shipment = self.source_docname
        elif self.source_doctype == "Air Booking":
            self.air_booking = self.source_docname
        elif self.source_doctype == "Sea Shipment":
            self.sea_shipment = self.source_docname
        elif self.source_doctype == "Sea Booking":
            self.sea_booking = self.source_docname


