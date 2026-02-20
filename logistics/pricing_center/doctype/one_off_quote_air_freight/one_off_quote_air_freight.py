# Copyright (c) 2025, www.agilasoft.com and contributors
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


class OneOffQuoteAirFreight(Document):
    """
    One-Off Quote Air Freight child table for air freight rate calculations
    Same structure and functionality as Sales Quote Air Freight
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calculator = TransportRateCalculationEngine()
    
    def validate(self):
        """Validate the one-off quote air freight record"""
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
            
            # Get tariff document
            tariff_doc = frappe.get_doc("Tariff", self.tariff)
            if not tariff_doc:
                frappe.msgprint(_("Tariff {0} not found").format(self.tariff), alert=True)
                return
            
            # Find matching transport rate in tariff
            matching_rate = self._find_matching_tariff_rate(tariff_doc)
            if not matching_rate:
                frappe.msgprint(_("No matching air freight rate found in tariff {0}").format(self.tariff), alert=True)
                return
            
            # Populate revenue fields if tariff is used for revenue
            if self.use_tariff_in_revenue:
                self._populate_revenue_from_tariff(matching_rate)
            
            # Populate cost fields if tariff is used for cost
            if self.use_tariff_in_cost:
                self._populate_cost_from_tariff(matching_rate)
                    
        except Exception as e:
            frappe.log_error(f"Error fetching tariff data: {str(e)}")
            frappe.msgprint(_("Error fetching tariff data: {0}").format(str(e)), alert=True)
    
    def _find_matching_tariff_rate(self, tariff_doc):
        """Find matching transport rate in tariff based on item code"""
        for rate in tariff_doc.transport_rates:
            if rate.item_code == self.item_code:
                return rate
        return None
    
    def _populate_revenue_from_tariff(self, tariff_rate):
        """Populate revenue fields from tariff data"""
        # Disable manual entry fields
        self._disable_revenue_fields()
        
        # Populate from tariff
        self.calculation_method = tariff_rate.calculation_method or "Per Unit"
        self.unit_rate = tariff_rate.rate or 0
        self.unit_type = tariff_rate.unit_type
        self.currency = tariff_rate.currency or "USD"
        self.minimum_quantity = tariff_rate.minimum_quantity or 0
        self.minimum_charge = tariff_rate.minimum_charge or 0
        self.maximum_charge = tariff_rate.maximum_charge or 0
        self.base_amount = tariff_rate.base_amount or 0
        self.uom = tariff_rate.uom
        
        # Trigger revenue calculation after populating tariff data
        self.calculate_estimated_revenue()
    
    def _populate_cost_from_tariff(self, tariff_rate):
        """Populate cost fields from tariff data"""
        # Disable manual entry fields
        self._disable_cost_fields()
        
        # Populate from tariff
        self.cost_calculation_method = tariff_rate.calculation_method or "Per Unit"
        self.unit_cost = tariff_rate.rate or 0
        self.cost_unit_type = tariff_rate.unit_type
        self.cost_currency = tariff_rate.currency or "USD"
        self.cost_minimum_quantity = tariff_rate.minimum_quantity or 0
        self.cost_minimum_charge = tariff_rate.minimum_charge or 0
        self.cost_maximum_charge = tariff_rate.maximum_charge or 0
        self.cost_base_amount = tariff_rate.base_amount or 0
        self.cost_uom = tariff_rate.uom
        
        # Trigger cost calculation after populating tariff data
        self.calculate_estimated_cost()
    
    def _disable_revenue_fields(self):
        """Disable revenue fields when using tariff"""
        # These fields will be read-only when tariff is used
        pass
    
    def _disable_cost_fields(self):
        """Disable cost fields when using tariff"""
        # These fields will be read-only when tariff is used
        pass
    
    def _validate_calculation_method_fields(self):
        """Validate fields based on revenue calculation method"""
        method = self.calculation_method
        
        if method == "Per Unit":
            if not self.unit_rate:
                frappe.throw(_("Unit Rate is required for Per Unit calculation"))
            if not self.unit_type:
                frappe.throw(_("Unit Type is required for Per Unit calculation"))
        
        elif method == "Fixed Amount":
            if not self.unit_rate:
                frappe.throw(_("Unit Rate is required for Fixed Amount calculation"))
        
        elif method == "Base Plus Additional":
            if not self.base_amount:
                frappe.throw(_("Base Amount is required for Base Plus Additional calculation"))
            if not self.unit_rate:
                frappe.throw(_("Unit Rate is required for Base Plus Additional calculation"))
        
        elif method == "First Plus Additional":
            if not self.unit_rate:
                frappe.throw(_("Unit Rate is required for First Plus Additional calculation"))
            if not self.minimum_quantity:
                frappe.throw(_("Minimum Quantity is required for First Plus Additional calculation"))
        
        elif method == "Percentage":
            if not self.base_amount:
                frappe.throw(_("Base Amount is required for Percentage calculation"))
            if not self.unit_rate:
                frappe.throw(_("Unit Rate (as percentage) is required for Percentage calculation"))
    
    def _validate_cost_calculation_method_fields(self):
        """Validate fields based on cost calculation method"""
        method = self.cost_calculation_method
        
        if method == "Per Unit":
            if not self.unit_cost:
                frappe.throw(_("Unit Cost is required for Per Unit cost calculation"))
            if not self.cost_unit_type:
                frappe.throw(_("Cost Unit Type is required for Per Unit cost calculation"))
        
        elif method == "Fixed Amount":
            if not self.unit_cost:
                frappe.throw(_("Unit Cost is required for Fixed Amount cost calculation"))
        
        elif method == "Base Plus Additional":
            if not self.cost_base_amount:
                frappe.throw(_("Cost Base Amount is required for Base Plus Additional cost calculation"))
            if not self.unit_cost:
                frappe.throw(_("Unit Cost is required for Base Plus Additional cost calculation"))
        
        elif method == "First Plus Additional":
            if not self.unit_cost:
                frappe.throw(_("Unit Cost is required for First Plus Additional cost calculation"))
            if not self.cost_minimum_quantity:
                frappe.throw(_("Cost Minimum Quantity is required for First Plus Additional cost calculation"))
        
        elif method == "Percentage":
            if not self.cost_base_amount:
                frappe.throw(_("Cost Base Amount is required for Percentage cost calculation"))
            if not self.unit_cost:
                frappe.throw(_("Unit Cost (as percentage) is required for Percentage cost calculation"))
    
    def calculate_quantities(self):
        """Calculate quantity based on calculation method"""
        if not self.calculation_method:
            return
        
        # Get parent document to access route information
        parent_doc = self.get_parent_doc()
        if not parent_doc:
            return
        
        # Calculate quantity based on calculation method
        if self.calculation_method == "Per Unit":
            self.quantity = self._calculate_per_unit_quantity(parent_doc)
        elif self.calculation_method == "Fixed Amount":
            # For Fixed Amount, preserve user-entered quantity or default to 1
            if not self.quantity or self.quantity == 0:
                self.quantity = 1
        elif self.calculation_method == "Base Plus Additional":
            self.quantity = self._calculate_base_plus_additional_quantity(parent_doc)
        elif self.calculation_method == "First Plus Additional":
            self.quantity = self._calculate_first_plus_additional_quantity(parent_doc)
        elif self.calculation_method == "Percentage":
            self.quantity = 1  # Percentage is based on base amount
        else:
            self.quantity = 1  # Default quantity
    
    def calculate_estimated_revenue(self):
        """Calculate estimated revenue based on calculation method"""
        if not self.calculation_method:
            self.estimated_revenue = 0
            self.revenue_calc_notes = "No calculation method specified"
            return
        
        # Handle Qty Break method separately
        if self.calculation_method == "Qty Break":
            self._calculate_qty_break_revenue()
            return
        
        if not self.unit_rate or self.unit_rate == 0:
            self.estimated_revenue = 0
            self.revenue_calc_notes = "No unit rate specified"
            return
        
        # Check for Percentage method - base_amount is required
        if self.calculation_method == "Percentage":
            if not self.base_amount or self.base_amount == 0:
                self.estimated_revenue = 0
                self.revenue_calc_notes = "Base Amount is required and must be greater than 0 for Percentage calculation"
                return
        
        try:
            # Prepare rate data for calculation
            rate_data = self._prepare_revenue_rate_data()
            
            # Get actual data from parent document
            actual_data = self._get_actual_data_from_parent()
            
            # Log calculation details for debugging
            frappe.logger().debug(f"One-Off Quote Air Freight Revenue Calculation - Item: {self.item_code}, "
                                 f"Method: {self.calculation_method}, Unit Type: {self.unit_type}, "
                                 f"Actual Data: {actual_data}")
            
            # Calculate rate using the transport rate calculation engine
            result = self.calculator.calculate_transport_rate(
                rate_data=rate_data,
                **actual_data
            )
            
            if result.get('success'):
                self.estimated_revenue = result.get('amount', 0)
                self.revenue_calc_notes = result.get('calculation_details', '')
                frappe.logger().debug(f"Revenue calculation successful: {self.estimated_revenue}")
            else:
                self.estimated_revenue = 0
                error_msg = result.get('error', 'Unknown error')
                self.revenue_calc_notes = f"Calculation failed: {error_msg}"
                frappe.log_error(f"Revenue calculation failed for {self.item_code}: {error_msg}")
                
        except Exception as e:
            error_msg = f"Revenue calculation error for {self.item_code}: {str(e)}"
            frappe.log_error(error_msg, "One-Off Quote Air Freight Calculation Error")
            self.estimated_revenue = 0
            self.revenue_calc_notes = f"Error: {str(e)}"
    
    def calculate_estimated_cost(self):
        """Calculate estimated cost based on cost calculation method"""
        if not self.cost_calculation_method:
            self.estimated_cost = 0
            self.cost_calc_notes = "No cost calculation method specified"
            return
        
        # Handle Qty Break method separately
        if self.cost_calculation_method == "Qty Break":
            self._calculate_qty_break_cost()
            return
        
        if not self.unit_cost or self.unit_cost == 0:
            self.estimated_cost = 0
            self.cost_calc_notes = "No unit cost specified"
            return
        
        # Check for Percentage method - cost_base_amount is required
        if self.cost_calculation_method == "Percentage":
            if not self.cost_base_amount or self.cost_base_amount == 0:
                self.estimated_cost = 0
                self.cost_calc_notes = "Cost Base Amount is required and must be greater than 0 for Percentage calculation"
                return
        
        try:
            # Prepare cost rate data for calculation
            cost_rate_data = self._prepare_cost_rate_data()
            
            # Validate cost rate data
            if not self._validate_cost_rate_data(cost_rate_data):
                self.estimated_cost = 0
                self.cost_calc_notes = "Invalid cost rate data for calculation"
                frappe.log_error(f"Invalid cost rate data for {self.item_code}", "One-Off Quote Air Freight Validation")
                return
            
            # Get actual data for cost calculation
            actual_data = self._get_cost_actual_data()
            
            # Log calculation details for debugging
            frappe.logger().debug(f"One-Off Quote Air Freight Cost Calculation - Item: {self.item_code}, "
                                 f"Method: {self.cost_calculation_method}, Unit Type: {self.cost_unit_type}, "
                                 f"Actual Data: {actual_data}")
            
            # Calculate cost using the transport rate calculation engine
            result = self.calculator.calculate_transport_rate(
                rate_data=cost_rate_data,
                **actual_data
            )
            
            if result.get('success'):
                self.estimated_cost = result.get('amount', 0)
                self.cost_calc_notes = result.get('calculation_details', '')
                frappe.logger().debug(f"Cost calculation successful: {self.estimated_cost}")
            else:
                self.estimated_cost = 0
                error_msg = result.get('error', 'Unknown error')
                self.cost_calc_notes = f"Cost calculation failed: {error_msg}"
                frappe.log_error(f"Cost calculation failed for {self.item_code}: {error_msg}")
                
        except Exception as e:
            error_msg = f"Cost calculation error for {self.item_code}: {str(e)}"
            frappe.log_error(error_msg, "One-Off Quote Air Freight Calculation Error")
            self.estimated_cost = 0
            self.cost_calc_notes = f"Error: {str(e)}"
    
    def _calculate_per_unit_quantity(self, parent_doc):
        """Calculate quantity for Per Unit method"""
        if not self.unit_type:
            return 1
        
        # Get quantity based on unit type from parent document
        # Use explicit None checks to handle 0 values correctly
        if self.unit_type == "Distance":
            return flt(parent_doc.get('total_distance') or 0)
        elif self.unit_type == "Weight":
            weight = parent_doc.get('weight')
            total_weight = parent_doc.get('total_weight')
            # Use explicit None check - 0 is a valid value
            if weight is not None:
                return flt(weight)
            elif total_weight is not None:
                return flt(total_weight)
            else:
                return 0
        elif self.unit_type == "Volume":
            volume = parent_doc.get('volume')
            total_volume = parent_doc.get('total_volume')
            # Use explicit None check - 0 is a valid value
            if volume is not None:
                return flt(volume)
            elif total_volume is not None:
                return flt(total_volume)
            else:
                return 0
        elif self.unit_type in ["Package", "Piece"]:
            return flt(parent_doc.get('total_pieces') or 0)
        elif self.unit_type == "TEU":
            return flt(parent_doc.get('total_teu') or 0)
        elif self.unit_type == "Operation Time":
            return flt(parent_doc.get('total_operation_time') or 0)
        else:
            return flt(self.quantity or 1)
    
    def _calculate_base_plus_additional_quantity(self, parent_doc):
        """Calculate quantity for Base Plus Additional method"""
        # For base plus additional, we need the additional quantity
        base_quantity = flt(self.minimum_quantity or 0)
        total_quantity = self._calculate_per_unit_quantity(parent_doc)
        return max(0, total_quantity - base_quantity)
    
    def _calculate_first_plus_additional_quantity(self, parent_doc):
        """Calculate quantity for First Plus Additional method"""
        # For first plus additional, we need the additional quantity beyond minimum
        minimum_quantity = flt(self.minimum_quantity or 0)
        total_quantity = self._calculate_per_unit_quantity(parent_doc)
        return max(0, total_quantity - minimum_quantity)
    
    def _prepare_revenue_rate_data(self):
        """Prepare rate data for revenue calculation"""
        return {
            'calculation_method': self.calculation_method,
            'rate': flt(self.unit_rate or 0),
            'unit_type': self.unit_type,
            'minimum_quantity': flt(self.minimum_quantity or 0),
            'minimum_charge': flt(self.minimum_charge or 0),
            'maximum_charge': flt(self.maximum_charge or 0),
            'base_amount': flt(self.base_amount or 0),
            'currency': self.currency or 'USD',
            'item_code': self.item_code,
            'item_name': self.item_name
        }
    
    def _prepare_cost_rate_data(self):
        """Prepare rate data for cost calculation"""
        return {
            'calculation_method': self.cost_calculation_method,
            'rate': flt(self.unit_cost or 0),
            'unit_type': self.cost_unit_type,
            'minimum_quantity': flt(self.cost_minimum_quantity or 0),
            'minimum_charge': flt(self.cost_minimum_charge or 0),
            'maximum_charge': flt(self.cost_maximum_charge or 0),
            'base_amount': flt(self.cost_base_amount or 0),
            'currency': self.cost_currency or 'USD',
            'item_code': self.item_code,
            'item_name': self.item_name
        }
    
    def _get_cost_actual_data(self):
        """Get actual data for cost calculation"""
        parent_doc = self.get_parent_doc()
        
        # Initialize with default values
        actual_data = {
            'actual_quantity': 0,
            'actual_weight': 0,
            'actual_volume': 0,
            'actual_distance': 0,
            'actual_pieces': 0,
            'actual_teu': 0,
            'actual_operation_time': 0
        }
        
        if not parent_doc:
            # If no parent doc, use the cost quantity from the line itself
            cost_qty = flt(self.cost_quantity or 0)
            actual_data['actual_quantity'] = cost_qty
            
            if self.cost_unit_type == 'Weight':
                actual_data['actual_weight'] = cost_qty
            elif self.cost_unit_type == 'Volume':
                actual_data['actual_volume'] = cost_qty
            elif self.cost_unit_type == 'Distance':
                actual_data['actual_distance'] = cost_qty
            elif self.cost_unit_type in ['Package', 'Piece']:
                actual_data['actual_pieces'] = cost_qty
            elif self.cost_unit_type == 'TEU':
                actual_data['actual_teu'] = cost_qty
            elif self.cost_unit_type == 'Operation Time':
                actual_data['actual_operation_time'] = cost_qty
        else:
            # Get weight with explicit None check
            weight = parent_doc.get('weight')
            total_weight = parent_doc.get('total_weight')
            if weight is not None:
                actual_data['actual_weight'] = flt(weight)
            elif total_weight is not None:
                actual_data['actual_weight'] = flt(total_weight)
            
            # Get volume with explicit None check
            volume = parent_doc.get('volume')
            total_volume = parent_doc.get('total_volume')
            if volume is not None:
                actual_data['actual_volume'] = flt(volume)
            elif total_volume is not None:
                actual_data['actual_volume'] = flt(total_volume)
            
            # Get other fields
            actual_data['actual_distance'] = flt(parent_doc.get('total_distance') or 0)
            actual_data['actual_pieces'] = flt(parent_doc.get('total_pieces') or 0)
            actual_data['actual_teu'] = flt(parent_doc.get('total_teu') or 0)
            actual_data['actual_operation_time'] = flt(parent_doc.get('total_operation_time') or 0)
            
            # Set actual_quantity based on cost_unit_type to ensure consistency
            if self.cost_unit_type == 'Weight':
                actual_data['actual_quantity'] = actual_data['actual_weight']
            elif self.cost_unit_type == 'Volume':
                actual_data['actual_quantity'] = actual_data['actual_volume']
            elif self.cost_unit_type == 'Distance':
                actual_data['actual_quantity'] = actual_data['actual_distance']
            elif self.cost_unit_type in ['Package', 'Piece']:
                actual_data['actual_quantity'] = actual_data['actual_pieces']
            elif self.cost_unit_type == 'TEU':
                actual_data['actual_quantity'] = actual_data['actual_teu']
            elif self.cost_unit_type == 'Operation Time':
                actual_data['actual_quantity'] = actual_data['actual_operation_time']
            else:
                # Fallback to cost_quantity if cost_unit_type is not standard
                actual_data['actual_quantity'] = flt(self.cost_quantity or 0)
        
        return actual_data
    
    def _get_actual_data_from_parent(self):
        """Get actual data from parent document for calculation"""
        parent_doc = self.get_parent_doc()
        
        # Initialize with default values
        actual_data = {
            'actual_quantity': 0,
            'actual_weight': 0,
            'actual_volume': 0,
            'actual_distance': 0,
            'actual_pieces': 0,
            'actual_teu': 0,
            'actual_operation_time': 0
        }
        
        # If parent doc exists, get values from parent
        if parent_doc:
            # Get weight with explicit None check
            weight = parent_doc.get('weight')
            total_weight = parent_doc.get('total_weight')
            if weight is not None:
                actual_data['actual_weight'] = flt(weight)
            elif total_weight is not None:
                actual_data['actual_weight'] = flt(total_weight)
            
            # Get volume with explicit None check
            volume = parent_doc.get('volume')
            total_volume = parent_doc.get('total_volume')
            if volume is not None:
                actual_data['actual_volume'] = flt(volume)
            elif total_volume is not None:
                actual_data['actual_volume'] = flt(total_volume)
            
            # Get other fields
            actual_data['actual_distance'] = flt(parent_doc.get('total_distance') or 0)
            actual_data['actual_pieces'] = flt(parent_doc.get('total_pieces') or 0)
            actual_data['actual_teu'] = flt(parent_doc.get('total_teu') or 0)
            actual_data['actual_operation_time'] = flt(parent_doc.get('total_operation_time') or 0)
            
            # Set actual_quantity based on unit_type to ensure consistency
            if self.unit_type == 'Weight':
                actual_data['actual_quantity'] = actual_data['actual_weight']
            elif self.unit_type == 'Volume':
                actual_data['actual_quantity'] = actual_data['actual_volume']
            elif self.unit_type == 'Distance':
                actual_data['actual_quantity'] = actual_data['actual_distance']
            elif self.unit_type in ['Package', 'Piece']:
                actual_data['actual_quantity'] = actual_data['actual_pieces']
            elif self.unit_type == 'TEU':
                actual_data['actual_quantity'] = actual_data['actual_teu']
            elif self.unit_type == 'Operation Time':
                actual_data['actual_quantity'] = actual_data['actual_operation_time']
            else:
                # Fallback to line quantity if unit_type is not standard
                actual_data['actual_quantity'] = flt(self.quantity or 0)
        else:
            # No parent doc - use line quantity and map to appropriate field
            line_quantity = flt(self.quantity or 0)
            actual_data['actual_quantity'] = line_quantity
            
            if self.unit_type == 'Weight':
                actual_data['actual_weight'] = line_quantity
            elif self.unit_type == 'Volume':
                actual_data['actual_volume'] = line_quantity
            elif self.unit_type == 'Distance':
                actual_data['actual_distance'] = line_quantity
            elif self.unit_type in ['Package', 'Piece']:
                actual_data['actual_pieces'] = line_quantity
            elif self.unit_type == 'TEU':
                actual_data['actual_teu'] = line_quantity
            elif self.unit_type == 'Operation Time':
                actual_data['actual_operation_time'] = line_quantity
        
        return actual_data
    
    def get_parent_doc(self):
        """Get parent document (One-Off Quote)"""
        if hasattr(self, 'parent') and self.parent:
            try:
                return frappe.get_doc(self.parenttype, self.parent)
            except Exception:
                return None
        return None
    
    def _validate_revenue_rate_data(self, rate_data):
        """Validate revenue rate data"""
        try:
            # Check required fields
            if not rate_data.get('calculation_method'):
                return False
            
            if not rate_data.get('rate') and rate_data.get('calculation_method') != 'Fixed Amount':
                return False
            
            # Check method-specific validations
            method = rate_data.get('calculation_method')
            
            if method == 'Base Plus Additional' and not rate_data.get('base_amount'):
                return False
            
            if method == 'First Plus Additional' and not rate_data.get('minimum_quantity'):
                return False
            
            if method == 'Percentage' and not rate_data.get('base_amount'):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _validate_cost_rate_data(self, rate_data):
        """Validate cost rate data"""
        try:
            # Check required fields
            if not rate_data.get('calculation_method'):
                return False
            
            if not rate_data.get('rate') and rate_data.get('calculation_method') not in ['Fixed Amount', 'Flat Rate']:
                return False
            
            # Check method-specific validations
            method = rate_data.get('calculation_method')
            
            if method == 'Base Plus Additional' and not rate_data.get('base_amount'):
                return False
            
            if method == 'First Plus Additional' and not rate_data.get('minimum_quantity'):
                return False
            
            if method == 'Percentage' and not rate_data.get('base_amount'):
                return False
            
            return True
            
        except Exception:
            return False
    
    def on_update(self):
        """Called when the document is updated"""
        self.handle_tariff_data()
        self.calculate_quantities()
        self.calculate_estimated_revenue()
        self.calculate_estimated_cost()
    
    def on_save(self):
        """Called when the document is saved"""
        self.handle_tariff_data()
        self.calculate_quantities()
        self.calculate_estimated_revenue()
        self.calculate_estimated_cost()
    
    def before_save(self):
        """Called before saving the document"""
        self.handle_tariff_data()
        self.calculate_quantities()
        self.calculate_estimated_revenue()
        self.calculate_estimated_cost()
    
    def trigger_calculations(self):
        """Trigger all calculations - can be called from client-side"""
        try:
            self.handle_tariff_data()
            self.calculate_quantities()
            self.calculate_estimated_revenue()
            self.calculate_estimated_cost()
            return True
        except Exception as e:
            frappe.log_error(f"Error in trigger_calculations: {str(e)}")
            return False
    
    def _calculate_qty_break_revenue(self):
        """Calculate revenue using qty break rates"""
        try:
            # Get actual quantity (package count)
            parent_doc = self.get_parent_doc()
            actual_qty = 0
            
            if parent_doc:
                # Try to get package count from parent
                if hasattr(parent_doc, 'total_pieces') and parent_doc.total_pieces:
                    actual_qty = flt(parent_doc.total_pieces)
                elif hasattr(parent_doc, 'packages') and parent_doc.packages:
                    actual_qty = len(parent_doc.packages)
                else:
                    actual_qty = flt(self.quantity or 0)
            else:
                actual_qty = flt(self.quantity or 0)
            
            if actual_qty <= 0:
                self.estimated_revenue = 0
                self.revenue_calc_notes = "No quantity available for qty break calculation"
                return
            
            # Get qty break rates
            qty_breaks = self._get_qty_break_rates('Selling')
            
            if not qty_breaks:
                self.estimated_revenue = 0
                self.revenue_calc_notes = "No qty break rates defined"
                return
            
            # Find applicable rate based on quantity
            applicable_rate = self._find_applicable_qty_break_rate(actual_qty, qty_breaks)
            
            if not applicable_rate:
                self.estimated_revenue = 0
                self.revenue_calc_notes = f"No applicable qty break rate found for quantity {actual_qty}"
                return
            
            # Calculate revenue: quantity * unit_rate
            self.estimated_revenue = flt(actual_qty) * flt(applicable_rate.get('unit_rate', 0))
            self.revenue_calc_notes = f"Qty Break: {actual_qty} packages × {applicable_rate.get('unit_rate', 0)} = {self.estimated_revenue} (Break: {applicable_rate.get('qty_break', 0)})"
            
        except Exception as e:
            frappe.log_error(f"Qty break revenue calculation error: {str(e)}")
            self.estimated_revenue = 0
            self.revenue_calc_notes = f"Error: {str(e)}"
    
    def _calculate_qty_break_cost(self):
        """Calculate cost using qty break rates"""
        try:
            # Get actual quantity (package count)
            parent_doc = self.get_parent_doc()
            actual_qty = 0
            
            if parent_doc:
                # Try to get package count from parent
                if hasattr(parent_doc, 'total_pieces') and parent_doc.total_pieces:
                    actual_qty = flt(parent_doc.total_pieces)
                elif hasattr(parent_doc, 'packages') and parent_doc.packages:
                    actual_qty = len(parent_doc.packages)
                else:
                    actual_qty = flt(self.cost_quantity or 0)
            else:
                actual_qty = flt(self.cost_quantity or 0)
            
            if actual_qty <= 0:
                self.estimated_cost = 0
                self.cost_calc_notes = "No quantity available for qty break calculation"
                return
            
            # Get qty break rates
            qty_breaks = self._get_qty_break_rates('Cost')
            
            if not qty_breaks:
                self.estimated_cost = 0
                self.cost_calc_notes = "No qty break rates defined"
                return
            
            # Find applicable rate based on quantity
            applicable_rate = self._find_applicable_qty_break_rate(actual_qty, qty_breaks)
            
            if not applicable_rate:
                self.estimated_cost = 0
                self.cost_calc_notes = f"No applicable qty break rate found for quantity {actual_qty}"
                return
            
            # Calculate cost: quantity * unit_rate
            self.estimated_cost = flt(actual_qty) * flt(applicable_rate.get('unit_rate', 0))
            self.cost_calc_notes = f"Qty Break: {actual_qty} packages × {applicable_rate.get('unit_rate', 0)} = {self.estimated_cost} (Break: {applicable_rate.get('qty_break', 0)})"
            
        except Exception as e:
            frappe.log_error(f"Qty break cost calculation error: {str(e)}")
            self.estimated_cost = 0
            self.cost_calc_notes = f"Error: {str(e)}"
    
    def _get_qty_break_rates(self, record_type='Selling'):
        """Get qty break rates for this air freight line"""
        if not self.name or self.name == 'new':
            return []
        
        try:
            qty_breaks = frappe.get_all(
                'Sales Quote Qty Break',
                filters={
                    'reference_doctype': 'One-Off Quote Air Freight',
                    'reference_no': self.name,
                    'type': record_type
                },
                fields=['qty_break', 'unit_rate', 'rate_type', 'currency'],
                order_by='qty_break asc'
            )
            return qty_breaks
        except Exception as e:
            frappe.log_error(f"Error getting qty break rates: {str(e)}")
            return []
    
    def _find_applicable_qty_break_rate(self, quantity, qty_breaks):
        """Find the applicable qty break rate for the given quantity"""
        if not qty_breaks:
            return None
        
        # Sort by qty_break descending to find the highest break that applies
        sorted_breaks = sorted(qty_breaks, key=lambda x: flt(x.get('qty_break', 0)), reverse=True)
        
        # Find the highest break that the quantity meets or exceeds
        for qb in sorted_breaks:
            if flt(quantity) >= flt(qb.get('qty_break', 0)):
                return qb
        
        # If no break applies, return the minimum break (lowest threshold)
        if sorted_breaks:
            return sorted(sorted_breaks, key=lambda x: flt(x.get('qty_break', 0)))[0]
        
        return None
    
    def get_calculation_summary(self):
        """Get summary of calculations"""
        return {
            'quantity': flt(self.quantity or 0),
            'estimated_revenue': flt(self.estimated_revenue or 0),
            'estimated_cost': flt(self.estimated_cost or 0),
            'revenue_calc_notes': self.revenue_calc_notes or '',
            'cost_calc_notes': self.cost_calc_notes or '',
            'calculation_method': self.calculation_method,
            'cost_calculation_method': self.cost_calculation_method,
            'use_tariff_in_revenue': self.use_tariff_in_revenue,
            'use_tariff_in_cost': self.use_tariff_in_cost,
            'tariff': self.tariff
        }


# API Functions

@frappe.whitelist()
def trigger_air_freight_calculations_for_line(line_data):
    """
    Trigger calculations for a specific one-off quote air freight line
    
    Args:
        line_data: JSON string or dict of line data
        
    Returns:
        Calculation result with revenue_calc_notes and cost_calc_notes
    """
    try:
        if isinstance(line_data, str):
            line_dict = json.loads(line_data)
        else:
            line_dict = line_data
        
        # Create a temporary document for calculation
        temp_doc = frappe.new_doc('One-Off Quote Air Freight')
        temp_doc.update(line_dict)
        
        # Trigger calculations
        success = temp_doc.trigger_calculations()
        
        if success:
            return {
                'success': True,
                'quantity': temp_doc.quantity,
                'estimated_revenue': temp_doc.estimated_revenue,
                'estimated_cost': temp_doc.estimated_cost,
                'revenue_calc_notes': temp_doc.revenue_calc_notes,
                'cost_calc_notes': temp_doc.cost_calc_notes
            }
        else:
            return {
                'success': False,
                'error': 'Calculation failed'
            }
        
    except Exception as e:
        frappe.log_error(f"Calculation error: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
