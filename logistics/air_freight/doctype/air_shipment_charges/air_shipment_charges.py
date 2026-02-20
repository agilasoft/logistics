# Copyright (c) 2025, logistics.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document


class AirShipmentCharges(Document):
    """
    Air Shipment Charges child table for pricing/charges
    """
    
    def validate(self):
        """Validate charge data"""
        self.validate_charge_data()
        self.calculate_charge_amount()
    
    def validate_charge_data(self):
        """Validate required fields"""
        if not self.item_code:
            frappe.throw(_("Item Code is required"))
        
        if not self.charge_type:
            frappe.throw(_("Charge Type is required"))
        
        if not self.charge_category:
            frappe.throw(_("Charge Category is required"))
        
        if not self.charge_basis:
            frappe.throw(_("Charge Basis is required"))
        
        if not self.rate:
            frappe.throw(_("Rate is required"))
        
        if not self.currency:
            frappe.throw(_("Currency is required"))
        
        # Validate rate is positive
        if flt(self.rate) <= 0:
            frappe.throw(_("Rate must be greater than zero"))
        
        # Validate quantity is positive if set
        if self.quantity and flt(self.quantity) < 0:
            frappe.throw(_("Quantity cannot be negative"))
    
    def calculate_charge_amount(self):
        """Calculate charge amount based on basis and quantity"""
        if not self.rate:
            self.base_amount = 0
            self.discount_amount = 0
            self.total_amount = 0
            return
        
        try:
            rate = flt(self.rate) or 0
            quantity = flt(self.quantity) or 0
            
            # Calculate base amount based on charge basis
            if self.charge_basis == "Per kg":
                if quantity > 0:
                    self.base_amount = rate * quantity
                else:
                    self.base_amount = 0
            elif self.charge_basis == "Per m³":
                if quantity > 0:
                    self.base_amount = rate * quantity
                else:
                    self.base_amount = 0
            elif self.charge_basis == "Per package":
                if quantity > 0:
                    self.base_amount = rate * quantity
                else:
                    self.base_amount = 0
            elif self.charge_basis == "Per shipment":
                self.base_amount = rate
            elif self.charge_basis == "Fixed amount":
                self.base_amount = rate
            elif self.charge_basis == "Percentage":
                # For percentage, we need the base value from parent Air Shipment
                if self.parent:
                    try:
                        air_shipment = frappe.get_doc("Air Shipment", self.parent)
                        # Use chargeable weight as base for percentage calculation
                        base_value = flt(air_shipment.chargeable) or flt(air_shipment.weight) or 0
                        self.base_amount = rate * (base_value * 0.01)
                    except Exception:
                        self.base_amount = 0
                else:
                    self.base_amount = 0
            else:
                self.base_amount = 0
            
            # Calculate discount amount
            if self.discount_percentage and self.base_amount:
                self.discount_amount = self.base_amount * (flt(self.discount_percentage) / 100)
            else:
                self.discount_amount = 0
            
            # Calculate surcharge amount (if set)
            surcharge = flt(self.surcharge_amount) or 0
            
            # Calculate tax amount (if set)
            tax = flt(self.tax_amount) or 0
            
            # Calculate total amount
            self.total_amount = self.base_amount - self.discount_amount + surcharge + tax
            
            # Ensure total amount is non-negative
            if self.total_amount < 0:
                self.total_amount = 0
                
        except Exception as e:
            frappe.log_error(f"Error calculating charge amount: {str(e)}", "Air Shipment Charges - Calculation")
            self.base_amount = 0
            self.discount_amount = 0
            self.total_amount = 0
    
    def on_update(self):
        """Called after saving"""
        # Recalculate if parent exists
        if self.parent:
            try:
                air_shipment = frappe.get_doc("Air Shipment", self.parent)
                # Trigger recalculation of total charges if needed
                if hasattr(air_shipment, 'calculate_total_charges'):
                    air_shipment.calculate_total_charges()
            except Exception:
                pass

