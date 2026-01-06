# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime


class LalamoveQuotation(Document):
    def validate(self):
        """Validate Lalamove Quotation"""
        # Ensure quotation_id is unique
        if self.quotation_id:
            existing = frappe.db.exists(
                "Lalamove Quotation",
                {
                    "quotation_id": self.quotation_id,
                    "name": ["!=", self.name]
                }
            )
            if existing:
                frappe.throw(f"Quotation ID {self.quotation_id} already exists")
        
        # Auto-populate module-specific links
        self._populate_module_links()
        
        # Check if quotation is expired
        self._check_expiry()
    
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
    
    def _check_expiry(self):
        """Check if quotation has expired"""
        if self.expires_at:
            try:
                expiry_time = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
                if datetime.now(expiry_time.tzinfo) >= expiry_time:
                    self.valid = 0
            except:
                pass


