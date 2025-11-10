# Copyright (c) 2025, logistics.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, cint, getdate, today
from frappe.model.document import Document
from typing import Dict, List, Optional, Any
from decimal import Decimal, ROUND_HALF_UP
import json

from logistics.pricing_center.api_parts.transport_rate_calculation_engine import (
    TransportRateCalculationEngine
)


class SalesQuoteAirFreight(Document):
    """
    Sales Quote Air Freight child table for air freight rate calculations
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calculator = TransportRateCalculationEngine()
    
    def validate(self):
        """Validate the sales quote air freight record"""
        self.validate_required_fields()
        self.handle_tariff_data()
        self.calculate_quantities()
        self.calculate_estimated_revenue()
        self.calculate_estimated_cost()
    
    def validate_required_fields(self):
        """Validate required fields based on calculation method"""
        # Only validate if we have the minimum required fields
        if not self.item_code:
            return  # Skip validation if no item code
        
        # Validate calculation method specific fields only if methods are set
        if self.calculation_method:
            self._validate_calculation_method_fields()
        
        if self.cost_calculation_method:
            self._validate_cost_calculation_method_fields()
    
    def handle_tariff_data(self):
        """Handle tariff data if tariff is selected"""
        if self.tariff and (self.use_tariff_in_revenue or self.use_tariff_in_cost):
            self._fetch_tariff_data()
    
    def _fetch_tariff_data(self):
        """Fetch tariff data and populate fields"""
        try:
            if not self.tariff:
                return
            
            tariff_doc = frappe.get_doc("Tariff", self.tariff)
            
            # Fetch revenue tariff data if enabled
            if self.use_tariff_in_revenue:
                if hasattr(tariff_doc, 'revenue_rate'):
                    self.unit_rate = tariff_doc.revenue_rate
                if hasattr(tariff_doc, 'revenue_calculation_method'):
                    self.calculation_method = tariff_doc.revenue_calculation_method
                if hasattr(tariff_doc, 'revenue_currency'):
                    self.currency = tariff_doc.revenue_currency
            
            # Fetch cost tariff data if enabled
            if self.use_tariff_in_cost:
                if hasattr(tariff_doc, 'cost_rate'):
                    self.unit_cost = tariff_doc.cost_rate
                if hasattr(tariff_doc, 'cost_calculation_method'):
                    self.cost_calculation_method = tariff_doc.cost_calculation_method
                if hasattr(tariff_doc, 'cost_currency'):
                    self.cost_currency = tariff_doc.cost_currency
                    
        except Exception as e:
            frappe.log_error(f"Error fetching tariff data: {str(e)}", "Sales Quote Air Freight - Tariff Fetch")
    
    def calculate_quantities(self):
        """Calculate quantities based on parent Sales Quote"""
        if not self.parent:
            return
        
        try:
            sales_quote = frappe.get_doc("Sales Quote", self.parent)
            
            # Map unit types to Sales Quote fields
            if self.unit_type == "Weight":
                self.quantity = flt(sales_quote.weight) or 0
            elif self.unit_type == "Volume":
                self.quantity = flt(sales_quote.volume) or 0
            elif self.unit_type == "Package":
                # Get package count from Sales Quote if available
                self.quantity = 1  # Default to 1 if not available
            elif self.unit_type == "Shipment":
                self.quantity = 1
            else:
                # For other unit types, keep existing quantity
                pass
            
            # Same for cost quantities
            if self.cost_unit_type == "Weight":
                self.cost_quantity = flt(sales_quote.weight) or 0
            elif self.cost_unit_type == "Volume":
                self.cost_quantity = flt(sales_quote.volume) or 0
            elif self.cost_unit_type == "Package":
                self.cost_quantity = 1
            elif self.cost_unit_type == "Shipment":
                self.cost_quantity = 1
                
        except Exception as e:
            frappe.log_error(f"Error calculating quantities: {str(e)}", "Sales Quote Air Freight - Quantity Calculation")
    
    def calculate_estimated_revenue(self):
        """Calculate estimated revenue based on calculation method"""
        if not self.calculation_method or not self.unit_rate:
            self.estimated_revenue = 0
            return
        
        try:
            quantity = flt(self.quantity) or 0
            rate = flt(self.unit_rate) or 0
            
            if self.calculation_method == "Per Unit":
                base_amount = rate * quantity
                # Apply minimum/maximum charge
                if self.minimum_charge and base_amount < flt(self.minimum_charge):
                    base_amount = flt(self.minimum_charge)
                if self.maximum_charge and base_amount > flt(self.maximum_charge):
                    base_amount = flt(self.maximum_charge)
                self.estimated_revenue = base_amount
                
            elif self.calculation_method == "Fixed Amount":
                self.estimated_revenue = rate
                
            elif self.calculation_method == "Base Plus Additional":
                base = flt(self.base_amount) or 0
                additional = rate * max(0, quantity - 1)
                self.estimated_revenue = base + additional
                
            elif self.calculation_method == "First Plus Additional":
                min_qty = flt(self.minimum_quantity) or 1
                if quantity <= min_qty:
                    self.estimated_revenue = rate
                else:
                    additional = rate * (quantity - min_qty)
                    self.estimated_revenue = rate + additional
                    
            elif self.calculation_method == "Percentage":
                # Percentage calculation requires base value from parent
                # For now, use rate as percentage of quantity
                self.estimated_revenue = (rate / 100) * quantity
            else:
                self.estimated_revenue = 0
                
        except Exception as e:
            frappe.log_error(f"Error calculating estimated revenue: {str(e)}", "Sales Quote Air Freight - Revenue Calculation")
            self.estimated_revenue = 0
    
    def calculate_estimated_cost(self):
        """Calculate estimated cost based on cost calculation method"""
        if not self.cost_calculation_method or not self.unit_cost:
            self.estimated_cost = 0
            return
        
        try:
            quantity = flt(self.cost_quantity) or 0
            cost = flt(self.unit_cost) or 0
            
            if self.cost_calculation_method == "Per Unit":
                base_amount = cost * quantity
                # Apply minimum/maximum charge
                if self.cost_minimum_charge and base_amount < flt(self.cost_minimum_charge):
                    base_amount = flt(self.cost_minimum_charge)
                if self.cost_maximum_charge and base_amount > flt(self.cost_maximum_charge):
                    base_amount = flt(self.cost_maximum_charge)
                self.estimated_cost = base_amount
                
            elif self.cost_calculation_method == "Fixed Amount":
                self.estimated_cost = cost
                
            elif self.cost_calculation_method == "Flat Rate":
                self.estimated_cost = cost
                
            elif self.cost_calculation_method == "Base Plus Additional":
                base = flt(self.cost_base_amount) or 0
                additional = cost * max(0, quantity - 1)
                self.estimated_cost = base + additional
                
            elif self.cost_calculation_method == "First Plus Additional":
                min_qty = flt(self.cost_minimum_quantity) or 1
                if quantity <= min_qty:
                    self.estimated_cost = cost
                else:
                    additional = cost * (quantity - min_qty)
                    self.estimated_cost = cost + additional
                    
            elif self.cost_calculation_method == "Percentage":
                # Percentage calculation requires base value from parent
                self.estimated_cost = (cost / 100) * quantity
            else:
                self.estimated_cost = 0
                
        except Exception as e:
            frappe.log_error(f"Error calculating estimated cost: {str(e)}", "Sales Quote Air Freight - Cost Calculation")
            self.estimated_cost = 0
    
    def _validate_calculation_method_fields(self):
        """Validate fields based on revenue calculation method"""
        if self.calculation_method == "Per Unit":
            if not self.unit_rate:
                frappe.throw(_("Unit Rate is required for Per Unit calculation method"))
            if not self.unit_type:
                frappe.throw(_("Unit Type is required for Per Unit calculation method"))
                
        elif self.calculation_method == "First Plus Additional":
            if not self.unit_rate:
                frappe.throw(_("Unit Rate is required for First Plus Additional calculation method"))
            if not self.minimum_quantity:
                frappe.throw(_("Minimum Quantity is required for First Plus Additional calculation method"))
                
        elif self.calculation_method == "Base Plus Additional":
            if not self.unit_rate:
                frappe.throw(_("Unit Rate is required for Base Plus Additional calculation method"))
            if not self.base_amount:
                frappe.throw(_("Base Amount is required for Base Plus Additional calculation method"))
                
        elif self.calculation_method == "Percentage":
            if not self.unit_rate:
                frappe.throw(_("Unit Rate is required for Percentage calculation method"))
    
    def _validate_cost_calculation_method_fields(self):
        """Validate fields based on cost calculation method"""
        if self.cost_calculation_method == "Per Unit":
            if not self.unit_cost:
                frappe.throw(_("Unit Cost is required for Per Unit cost calculation method"))
            if not self.cost_unit_type:
                frappe.throw(_("Cost Unit Type is required for Per Unit cost calculation method"))
                
        elif self.cost_calculation_method == "First Plus Additional":
            if not self.unit_cost:
                frappe.throw(_("Unit Cost is required for First Plus Additional cost calculation method"))
            if not self.cost_minimum_quantity:
                frappe.throw(_("Cost Minimum Quantity is required for First Plus Additional cost calculation method"))
                
        elif self.cost_calculation_method == "Base Plus Additional":
            if not self.unit_cost:
                frappe.throw(_("Unit Cost is required for Base Plus Additional cost calculation method"))
            if not self.cost_base_amount:
                frappe.throw(_("Cost Base Amount is required for Base Plus Additional cost calculation method"))

