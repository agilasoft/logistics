# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, cint, getdate, today
from typing import Dict, List, Optional, Any
from decimal import Decimal, ROUND_HALF_UP
import json


class TransportRateCalculationEngine:
    """
    Final Transport Rate Calculation Engine
    
    This is the definitive calculation engine for Transport Rate in the pricing_center.
    Focused specifically on Transport Rate calculations that can be pulled by Sales Quote.
    
    Key Features:
    1. All calculation methods for Transport Rate
    2. Location-based rate matching
    3. Vehicle type and load type considerations
    4. Minimum/Maximum charge handling
    5. Currency conversion support
    6. Sales Quote integration ready
    """
    
    def __init__(self):
        self.calculation_methods = {
            'Per Unit': self._calculate_per_unit,
            'Fixed Amount': self._calculate_fixed_amount,
            'Flat Rate': self._calculate_flat_rate,
            'Base Plus Additional': self._calculate_base_plus_additional,
            'First Plus Additional': self._calculate_first_plus_additional,
            'Percentage': self._calculate_percentage,
            'Location-based': self._calculate_location_based
        }
        
        self.unit_types = {
            'Distance': 'km',
            'Weight': 'kg',
            'Volume': 'm3',
            'Package': 'pcs',
            'Piece': 'pcs',
            'Job': 'job',
            'Trip': 'trip',
            'TEU': 'teu',
            'Operation Time': 'hrs'
        }
    
    def calculate_transport_rate(self, 
                                rate_data: Dict,
                                actual_quantity: float = 0,
                                actual_weight: float = 0,
                                actual_volume: float = 0,
                                actual_distance: float = 0,
                                actual_pieces: int = 0,
                                **kwargs) -> Dict:
        """
        Main calculation method for Transport Rate
        
        Args:
            rate_data: Transport Rate configuration from Tariff
            actual_quantity: Actual quantity for calculation
            actual_weight: Actual weight in KG
            actual_volume: Actual volume in M3
            actual_distance: Actual distance in KM
            actual_pieces: Actual number of pieces
            **kwargs: Additional parameters
            
        Returns:
            Dict containing calculated rate information
        """
        
        try:
            # Validate rate data
            if not rate_data:
                return self._create_error_result("Rate data is required")
            
            # Get calculation method
            calculation_method = rate_data.get('calculation_method', 'Per Unit')
            
            if calculation_method not in self.calculation_methods:
                return self._create_error_result(f"Invalid calculation method: {calculation_method}")
            
            # Calculate base amount
            base_amount = self.calculation_methods[calculation_method](
                rate_data=rate_data,
                actual_quantity=actual_quantity,
                actual_weight=actual_weight,
                actual_volume=actual_volume,
                actual_distance=actual_distance,
                actual_pieces=actual_pieces,
                **kwargs
            )
            
            # Apply minimum and maximum charges
            final_amount = self._apply_min_max_charges(base_amount, rate_data)
            
            # Round to 2 decimal places
            final_amount = float(Decimal(str(final_amount)).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            ))
            
            return {
                'success': True,
                'amount': final_amount,
                'base_amount': base_amount,
                'calculation_method': calculation_method,
                'rate_data': rate_data,
                'calculation_details': self._get_calculation_details(
                    calculation_method, rate_data, final_amount
                ),
                'currency': rate_data.get('currency', 'USD'),
                'item_code': rate_data.get('item_code'),
                'item_name': rate_data.get('item_name')
            }
            
        except Exception as e:
            frappe.log_error(f"Transport rate calculation error: {str(e)}")
            return self._create_error_result(f"Calculation failed: {str(e)}")
    
    def _calculate_per_unit(self, rate_data: Dict, **kwargs) -> float:
        """Calculate rate using Per Unit method"""
        rate = flt(rate_data.get('rate', 0))
        unit_type = rate_data.get('unit_type', 'Weight')
        actual_quantity = kwargs.get('actual_quantity', 0)
        
        # Get actual quantity based on unit type
        if unit_type == 'Weight':
            quantity = kwargs.get('actual_weight', 0)
        elif unit_type == 'Volume':
            quantity = kwargs.get('actual_volume', 0)
        elif unit_type == 'Distance':
            quantity = kwargs.get('actual_distance', 0)
        elif unit_type in ['Package', 'Piece']:
            quantity = kwargs.get('actual_pieces', 0)
        else:
            quantity = actual_quantity
        
        return rate * quantity
    
    def _calculate_fixed_amount(self, rate_data: Dict, **kwargs) -> float:
        """Calculate rate using Fixed Amount method"""
        return flt(rate_data.get('fixed_amount', 0))
    
    def _calculate_flat_rate(self, rate_data: Dict, **kwargs) -> float:
        """Calculate rate using Flat Rate method"""
        return flt(rate_data.get('rate', 0))
    
    def _calculate_base_plus_additional(self, rate_data: Dict, **kwargs) -> float:
        """Calculate rate using Base Plus Additional method"""
        base_amount = flt(rate_data.get('base_amount', 0))
        rate = flt(rate_data.get('rate', 0))
        unit_type = rate_data.get('unit_type', 'Weight')
        
        # Get additional quantity
        if unit_type == 'Weight':
            additional_quantity = kwargs.get('actual_weight', 0)
        elif unit_type == 'Volume':
            additional_quantity = kwargs.get('actual_volume', 0)
        elif unit_type == 'Distance':
            additional_quantity = kwargs.get('actual_distance', 0)
        elif unit_type in ['Package', 'Piece']:
            additional_quantity = kwargs.get('actual_pieces', 0)
        else:
            additional_quantity = kwargs.get('actual_quantity', 0)
        
        additional_amount = rate * additional_quantity
        return base_amount + additional_amount
    
    def _calculate_first_plus_additional(self, rate_data: Dict, **kwargs) -> float:
        """Calculate rate using First Plus Additional method"""
        rate = flt(rate_data.get('rate', 0))
        minimum_quantity = flt(rate_data.get('minimum_quantity', 0))
        unit_type = rate_data.get('unit_type', 'Weight')
        
        # Get actual quantity
        if unit_type == 'Weight':
            actual_quantity = kwargs.get('actual_weight', 0)
        elif unit_type == 'Volume':
            actual_quantity = kwargs.get('actual_volume', 0)
        elif unit_type == 'Distance':
            actual_quantity = kwargs.get('actual_distance', 0)
        elif unit_type in ['Package', 'Piece']:
            actual_quantity = kwargs.get('actual_pieces', 0)
        else:
            actual_quantity = kwargs.get('actual_quantity', 0)
        
        if actual_quantity <= minimum_quantity:
            return rate
        else:
            additional_quantity = actual_quantity - minimum_quantity
            return rate + (rate * 0.5 * additional_quantity)  # 50% of rate for additional
    
    def _calculate_percentage(self, rate_data: Dict, **kwargs) -> float:
        """Calculate rate using Percentage method"""
        base_amount = flt(rate_data.get('base_amount', 0))
        percentage = flt(rate_data.get('rate', 0))  # Rate field used as percentage
        return base_amount * (percentage / 100)
    
    def _calculate_location_based(self, rate_data: Dict, **kwargs) -> float:
        """Calculate rate using Location-based method"""
        # This method would typically involve zone-based calculations
        # For now, fall back to per unit calculation
        return self._calculate_per_unit(rate_data, **kwargs)
    
    def _apply_min_max_charges(self, amount: float, rate_data: Dict) -> float:
        """Apply minimum and maximum charges"""
        min_charge = flt(rate_data.get('minimum_charge', 0))
        max_charge = flt(rate_data.get('maximum_charge', 0))
        
        if min_charge > 0 and amount < min_charge:
            amount = min_charge
        
        if max_charge > 0 and amount > max_charge:
            amount = max_charge
        
        return amount
    
    def _get_calculation_details(self, method: str, rate_data: Dict, amount: float) -> str:
        """Get human-readable calculation details"""
        rate = flt(rate_data.get('rate', 0))
        unit_type = rate_data.get('unit_type', 'Weight')
        
        if method == 'Per Unit':
            return f"Rate: {rate} × {unit_type} = {amount}"
        elif method == 'Fixed Amount':
            return f"Fixed Amount: {amount}"
        elif method == 'Flat Rate':
            return f"Flat Rate: {amount}"
        elif method == 'Base Plus Additional':
            base_amount = flt(rate_data.get('base_amount', 0))
            return f"Base: {base_amount} + Additional: {amount - base_amount} = {amount}"
        elif method == 'First Plus Additional':
            return f"First: {rate} + Additional charges = {amount}"
        elif method == 'Percentage':
            return f"Base: {flt(rate_data.get('base_amount', 0))} × {rate}% = {amount}"
        else:
            return f"Calculated: {amount}"
    
    def _create_error_result(self, message: str) -> Dict:
        """Create error result"""
        return {
            'success': False,
            'error': message,
            'amount': 0
        }
    
    def get_matching_rates(self, 
                          origin_location: str = None,
                          destination_location: str = None,
                          vehicle_type: str = None,
                          load_type: str = None,
                          container_type: str = None,
                          tariff_name: str = None,
                          **kwargs) -> List[Dict]:
        """
        Get matching transport rates based on criteria
        
        Args:
            origin_location: Origin location/zone
            destination_location: Destination location/zone
            vehicle_type: Type of vehicle
            load_type: Type of load
            container_type: Type of container
            tariff_name: Specific tariff to use
            **kwargs: Additional filters
            
        Returns:
            List of matching rate configurations
        """
        
        try:
            # Build filters
            filters = {
                'enabled': 1
            }
            
            if tariff_name:
                # Get rates from specific tariff
                tariff_doc = frappe.get_doc('Tariff', tariff_name)
                rates = []
                for rate in tariff_doc.transport_rates:
                    rate_dict = rate.as_dict()
                    if self._matches_criteria(rate_dict, origin_location, destination_location, 
                                            vehicle_type, load_type, container_type):
                        rates.append(rate_dict)
                return rates
            else:
                # Search all transport rates
                filters.update({
                    'location_from': origin_location,
                    'location_to': destination_location,
                    'vehicle_type': vehicle_type,
                    'load_type': load_type,
                    'container_type': container_type
                })
                
                # Remove None values
                filters = {k: v for k, v in filters.items() if v is not None}
                
                rates = frappe.get_all('Transport Rate', 
                                     filters=filters,
                                     fields=['*'])
                
                return rates
                
        except Exception as e:
            frappe.log_error(f"Error getting matching rates: {str(e)}")
            return []
    
    def _matches_criteria(self, rate_data: Dict, origin: str, destination: str,
                         vehicle_type: str, load_type: str, container_type: str) -> bool:
        """Check if rate matches the given criteria"""
        
        if origin and rate_data.get('location_from') != origin:
            return False
        
        if destination and rate_data.get('location_to') != destination:
            return False
        
        if vehicle_type and rate_data.get('vehicle_type') != vehicle_type:
            return False
        
        if load_type and rate_data.get('load_type') != load_type:
            return False
        
        if container_type and rate_data.get('container_type') != container_type:
            return False
        
        return True
    
    def calculate_bulk_rates(self, 
                           rate_configurations: List[Dict],
                           actual_data: Dict) -> List[Dict]:
        """
        Calculate rates for multiple configurations
        
        Args:
            rate_configurations: List of rate configurations
            actual_data: Actual data for calculation
            
        Returns:
            List of calculation results
        """
        
        results = []
        
        for rate_config in rate_configurations:
            result = self.calculate_transport_rate(
                rate_data=rate_config,
                **actual_data
            )
            results.append(result)
        
        return results


# API Functions for Sales Quote Integration

@frappe.whitelist()
def calculate_transport_rate_for_quote(rate_data: str, **kwargs) -> Dict:
    """
    API endpoint for Sales Quote to calculate transport rates
    
    Args:
        rate_data: JSON string of rate configuration
        **kwargs: Actual data for calculation
        
    Returns:
        Calculation result
    """
    
    try:
        # Parse rate data
        if isinstance(rate_data, str):
            rate_config = json.loads(rate_data)
        else:
            rate_config = rate_data
        
        # Initialize calculator
        calculator = TransportRateCalculationEngine()
        
        # Calculate rate
        result = calculator.calculate_transport_rate(
            rate_data=rate_config,
            **kwargs
        )
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Transport rate calculation API error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'amount': 0
        }


@frappe.whitelist()
def get_transport_rates_for_route(origin: str = None, 
                                 destination: str = None,
                                 vehicle_type: str = None,
                                 load_type: str = None,
                                 container_type: str = None,
                                 tariff_name: str = None) -> List[Dict]:
    """
    API endpoint to get transport rates for a specific route
    
    Args:
        origin: Origin location
        destination: Destination location
        vehicle_type: Vehicle type
        load_type: Load type
        container_type: Container type
        tariff_name: Specific tariff
        
    Returns:
        List of matching rates
    """
    
    try:
        calculator = TransportRateCalculationEngine()
        
        rates = calculator.get_matching_rates(
            origin_location=origin,
            destination_location=destination,
            vehicle_type=vehicle_type,
            load_type=load_type,
            container_type=container_type,
            tariff_name=tariff_name
        )
        
        return rates
        
    except Exception as e:
        frappe.log_error(f"Get transport rates API error: {str(e)}")
        return []


@frappe.whitelist()
def calculate_bulk_transport_rates(rate_configurations: str, actual_data: str) -> List[Dict]:
    """
    API endpoint to calculate multiple transport rates at once
    
    Args:
        rate_configurations: JSON string of rate configurations
        actual_data: JSON string of actual data
        
    Returns:
        List of calculation results
    """
    
    try:
        # Parse inputs
        if isinstance(rate_configurations, str):
            rate_configs = json.loads(rate_configurations)
        else:
            rate_configs = rate_configurations
        
        if isinstance(actual_data, str):
            actual_data_dict = json.loads(actual_data)
        else:
            actual_data_dict = actual_data
        
        # Initialize calculator
        calculator = TransportRateCalculationEngine()
        
        # Calculate rates
        results = calculator.calculate_bulk_rates(
            rate_configurations=rate_configs,
            actual_data=actual_data_dict
        )
        
        return results
        
    except Exception as e:
        frappe.log_error(f"Bulk transport rate calculation API error: {str(e)}")
        return []


# Utility Functions

def get_available_calculation_methods() -> List[str]:
    """Get list of available calculation methods"""
    return [
        'Per Unit',
        'Fixed Amount', 
        'Flat Rate',
        'Base Plus Additional',
        'First Plus Additional',
        'Percentage',
        'Location-based'
    ]


def get_available_unit_types() -> List[str]:
    """Get list of available unit types"""
    return [
        'Distance',
        'Weight',
        'Volume',
        'Package',
        'Piece',
        'Job',
        'Trip',
        'TEU',
        'Operation Time'
    ]


def validate_rate_data(rate_data: Dict) -> Dict:
    """
    Validate rate data before calculation
    
    Args:
        rate_data: Rate configuration to validate
        
    Returns:
        Validation result
    """
    
    errors = []
    
    # Check required fields
    if not rate_data.get('calculation_method'):
        errors.append("Calculation method is required")
    
    if not rate_data.get('rate') and rate_data.get('calculation_method') != 'Fixed Amount':
        errors.append("Rate is required")
    
    if not rate_data.get('currency'):
        errors.append("Currency is required")
    
    # Check calculation method specific validations
    method = rate_data.get('calculation_method')
    
    if method == 'Base Plus Additional' and not rate_data.get('base_amount'):
        errors.append("Base amount is required for Base Plus Additional method")
    
    if method == 'First Plus Additional' and not rate_data.get('minimum_quantity'):
        errors.append("Minimum quantity is required for First Plus Additional method")
    
    if method == 'Percentage' and not rate_data.get('base_amount'):
        errors.append("Base amount is required for Percentage method")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }





