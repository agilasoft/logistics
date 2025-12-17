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


class SalesQuoteSeaFreight(Document):
    """
    Sales Quote Sea Freight child table for sea freight rate calculations
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calculator = TransportRateCalculationEngine()
    
    def validate(self):
        """Validate the sales quote sea freight record"""
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
                frappe.msgprint(_("No matching sea freight rate found in tariff {0}").format(self.tariff), alert=True)
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
            
            # Calculate rate using the transport rate calculation engine
            result = self.calculator.calculate_transport_rate(
                rate_data=rate_data,
                **actual_data
            )
            
            if result.get('success'):
                self.estimated_revenue = result.get('amount', 0)
                self.revenue_calc_notes = result.get('calculation_details', '')
            else:
                self.estimated_revenue = 0
                self.revenue_calc_notes = f"Calculation failed: {result.get('error', 'Unknown error')}"
                
        except Exception as e:
            frappe.log_error(f"Revenue calculation error: {str(e)}")
            self.estimated_revenue = 0
            self.revenue_calc_notes = f"Error: {str(e)}"
    
    def calculate_estimated_cost(self):
        """Calculate estimated cost based on cost calculation method"""
        if not self.cost_calculation_method:
            self.estimated_cost = 0
            self.cost_calc_notes = "No cost calculation method specified"
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
                return
            
            # Get actual data for cost calculation
            actual_data = self._get_cost_actual_data()
            
            # Calculate cost using the transport rate calculation engine
            result = self.calculator.calculate_transport_rate(
                rate_data=cost_rate_data,
                **actual_data
            )
            
            if result.get('success'):
                self.estimated_cost = result.get('amount', 0)
                self.cost_calc_notes = result.get('calculation_details', '')
            else:
                self.estimated_cost = 0
                self.cost_calc_notes = f"Cost calculation failed: {result.get('error', 'Unknown error')}"
                
        except Exception as e:
            frappe.log_error(f"Cost calculation error: {str(e)}")
            self.estimated_cost = 0
            self.cost_calc_notes = f"Error: {str(e)}"
    
    def _calculate_per_unit_quantity(self, parent_doc):
        """Calculate quantity for Per Unit method"""
        if not self.unit_type:
            return 1
        
        # Get quantity based on unit type from parent document
        if self.unit_type == "Distance":
            return flt(parent_doc.get('total_distance', 0))
        elif self.unit_type == "Weight":
            return flt(parent_doc.get('weight', 0) or parent_doc.get('total_weight', 0))
        elif self.unit_type == "Volume":
            return flt(parent_doc.get('volume', 0) or parent_doc.get('total_volume', 0))
        elif self.unit_type in ["Package", "Piece"]:
            return flt(parent_doc.get('total_pieces', 0))
        elif self.unit_type == "TEU":
            return flt(parent_doc.get('total_teu', 0))
        elif self.unit_type == "Container":
            return flt(parent_doc.get('total_containers', 0) or parent_doc.get('total_teu', 0))
        elif self.unit_type == "Shipment":
            return 1
        elif self.unit_type == "Operation Time":
            return flt(parent_doc.get('total_operation_time', 0))
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
        if not parent_doc:
            # If no parent doc, use the cost quantity from the line itself
            return {
                'actual_quantity': flt(self.cost_quantity or 0),
                'actual_weight': flt(self.cost_quantity or 0) if self.cost_unit_type == 'Weight' else 0,
                'actual_volume': flt(self.cost_quantity or 0) if self.cost_unit_type == 'Volume' else 0,
                'actual_distance': flt(self.cost_quantity or 0) if self.cost_unit_type == 'Distance' else 0,
                'actual_pieces': flt(self.cost_quantity or 0) if self.cost_unit_type in ['Package', 'Piece'] else 0,
                'actual_teu': flt(self.cost_quantity or 0) if self.cost_unit_type == 'TEU' else 0,
                'actual_containers': flt(self.cost_quantity or 0) if self.cost_unit_type == 'Container' else 0,
                'actual_operation_time': flt(self.cost_quantity or 0) if self.cost_unit_type == 'Operation Time' else 0
            }
        
        return {
            'actual_quantity': flt(self.cost_quantity or 0),
            'actual_weight': flt(parent_doc.get('weight', 0) or parent_doc.get('total_weight', 0)),
            'actual_volume': flt(parent_doc.get('volume', 0) or parent_doc.get('total_volume', 0)),
            'actual_distance': flt(parent_doc.get('total_distance', 0)),
            'actual_pieces': flt(parent_doc.get('total_pieces', 0)),
            'actual_teu': flt(parent_doc.get('total_teu', 0)),
            'actual_containers': flt(parent_doc.get('total_containers', 0) or parent_doc.get('total_teu', 0)),
            'actual_operation_time': flt(parent_doc.get('total_operation_time', 0))
        }
    
    def _get_actual_data_from_parent(self):
        """Get actual data from parent document for calculation"""
        parent_doc = self.get_parent_doc()
        
        # Use quantity from the line itself for calculations
        line_quantity = flt(self.quantity or 0)
        
        # Map quantity to appropriate field based on unit type
        actual_data = {
            'actual_quantity': line_quantity,
            'actual_weight': line_quantity if self.unit_type == 'Weight' else 0,
            'actual_volume': line_quantity if self.unit_type == 'Volume' else 0,
            'actual_distance': line_quantity if self.unit_type == 'Distance' else 0,
            'actual_pieces': line_quantity if self.unit_type in ['Package', 'Piece'] else 0,
            'actual_teu': line_quantity if self.unit_type == 'TEU' else 0,
            'actual_containers': line_quantity if self.unit_type == 'Container' else 0,
            'actual_operation_time': line_quantity if self.unit_type == 'Operation Time' else 0
        }
        
        # If parent doc exists, try to get additional data
        if parent_doc:
            actual_data.update({
                'actual_weight': flt(parent_doc.get('weight', 0) or parent_doc.get('total_weight', actual_data['actual_weight'])),
                'actual_volume': flt(parent_doc.get('volume', 0) or parent_doc.get('total_volume', actual_data['actual_volume'])),
                'actual_distance': flt(parent_doc.get('total_distance', actual_data['actual_distance'])),
                'actual_pieces': flt(parent_doc.get('total_pieces', actual_data['actual_pieces'])),
                'actual_teu': flt(parent_doc.get('total_teu', actual_data['actual_teu'])),
                'actual_containers': flt(parent_doc.get('total_containers', 0) or parent_doc.get('total_teu', actual_data['actual_containers'])),
                'actual_operation_time': flt(parent_doc.get('total_operation_time', actual_data['actual_operation_time']))
            })
        
        return actual_data
    
    def get_parent_doc(self):
        """Get parent document (Sales Quote)"""
        if hasattr(self, 'parent') and self.parent:
            try:
                return frappe.get_doc(self.parenttype, self.parent)
            except:
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
def calculate_sea_freight_line(line_data):
    """
    API endpoint to calculate sea freight line rates
    
    Args:
        line_data: JSON string of line data
        
    Returns:
        Calculation result
    """
    try:
        if isinstance(line_data, str):
            line_dict = json.loads(line_data)
        else:
            line_dict = line_data
        
        # Create a temporary document for calculation
        temp_doc = frappe.new_doc('Sales Quote Sea Freight')
        temp_doc.update(line_dict)
        
        # Calculate quantities and rates
        temp_doc.calculate_quantities()
        temp_doc.calculate_estimated_revenue()
        temp_doc.calculate_estimated_cost()
        
        return {
            'success': True,
            'quantity': temp_doc.quantity,
            'estimated_revenue': temp_doc.estimated_revenue,
            'estimated_cost': temp_doc.estimated_cost,
            'revenue_calc_notes': temp_doc.revenue_calc_notes,
            'cost_calc_notes': temp_doc.cost_calc_notes
        }
        
    except Exception as e:
        frappe.log_error(f"Sea freight line calculation error: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@frappe.whitelist()
def get_sea_freight_calculation_methods():
    """Get available calculation methods"""
    return [
        'Per Unit',
        'Fixed Amount',
        'Base Plus Additional',
        'First Plus Additional',
        'Percentage'
    ]


@frappe.whitelist()
def get_sea_freight_cost_calculation_methods():
    """Get available cost calculation methods"""
    return [
        'Per Unit',
        'Fixed Amount',
        'Flat Rate',
        'Base Plus Additional',
        'First Plus Additional',
        'Percentage',
        'Location-based'
    ]


@frappe.whitelist()
def get_sea_freight_unit_types():
    """Get available unit types"""
    return [
        'Distance',
        'Weight',
        'Volume',
        'Package',
        'Piece',
        'Shipment',
        'Container',
        'TEU',
        'Operation Time'
    ]


@frappe.whitelist()
def get_sea_freight_tariff_rates(tariff_name, item_code=None):
    """
    Get sea freight rates from a tariff
    
    Args:
        tariff_name: Name of the tariff
        item_code: Optional item code to filter rates
        
    Returns:
        List of matching rates
    """
    try:
        if not tariff_name:
            return []
        
        # Get tariff document
        tariff_doc = frappe.get_doc("Tariff", tariff_name)
        if not tariff_doc:
            return []
        
        rates = []
        for rate in tariff_doc.transport_rates:
            if not item_code or rate.item_code == item_code:
                rates.append({
                    'item_code': rate.item_code,
                    'item_name': rate.item_name,
                    'calculation_method': rate.calculation_method,
                    'rate': rate.rate,
                    'unit_type': rate.unit_type,
                    'currency': rate.currency,
                    'minimum_quantity': rate.minimum_quantity,
                    'minimum_charge': rate.minimum_charge,
                    'maximum_charge': rate.maximum_charge,
                    'base_amount': rate.base_amount,
                    'uom': rate.uom
                })
        
        return rates
        
    except Exception as e:
        frappe.log_error(f"Error getting tariff rates: {str(e)}")
        return []


@frappe.whitelist()
def trigger_sea_freight_calculations_for_line(line_data):
    """
    Trigger calculations for a specific sea freight line
    
    Args:
        line_data: JSON string of line data
        
    Returns:
        Calculation result
    """
    try:
        if isinstance(line_data, str):
            line_dict = json.loads(line_data)
        else:
            line_dict = line_data
        
        # Create a temporary document for calculation
        temp_doc = frappe.new_doc('Sales Quote Sea Freight')
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
