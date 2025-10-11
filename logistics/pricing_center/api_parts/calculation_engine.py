# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from typing import Dict, List, Optional, Any
from .transport_rate_calculation_engine import TransportRateCalculationEngine, get_available_calculation_methods


def calculate_rate(calculation_method: str, rate_value: float, service_type: str = "Transport", **kwargs) -> Dict:
    """
    Calculate rate using the specified calculation method
    
    Args:
        calculation_method: Method to use for calculation
        rate_value: Base rate value
        service_type: Type of service (Transport, etc.)
        **kwargs: Additional parameters for calculation
        
    Returns:
        Dict containing calculation result
    """
    
    try:
        # Create rate data from parameters
        rate_data = {
            'calculation_method': calculation_method,
            'rate': rate_value,
            'currency': kwargs.get('currency', 'USD'),
            'unit_type': kwargs.get('unit_type', 'Weight'),
            'minimum_charge': kwargs.get('minimum_charge', 0),
            'maximum_charge': kwargs.get('maximum_charge', 0),
            'base_amount': kwargs.get('base_amount', 0),
            'minimum_quantity': kwargs.get('minimum_quantity', 0),
            'fixed_amount': kwargs.get('fixed_amount', 0)
        }
        
        # Initialize calculator
        calculator = TransportRateCalculationEngine()
        
        # Calculate rate
        result = calculator.calculate_transport_rate(
            rate_data=rate_data,
            actual_quantity=kwargs.get('actual_quantity', 0),
            actual_weight=kwargs.get('actual_weight', 0),
            actual_volume=kwargs.get('actual_volume', 0),
            actual_distance=kwargs.get('actual_distance', 0),
            actual_pieces=kwargs.get('actual_pieces', 0),
            **kwargs
        )
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Rate calculation error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'amount': 0
        }


def get_available_methods(service_type: str = "Transport") -> List[str]:
    """
    Get available calculation methods for a service type
    
    Args:
        service_type: Type of service
        
    Returns:
        List of available calculation methods
    """
    
    if service_type == "Transport":
        return get_available_calculation_methods()
    else:
        # For other service types, return basic methods
        return [
            'Per Unit',
            'Fixed Amount',
            'Flat Rate'
        ]


def get_matching_rates(service_type: str = "Transport", **filters) -> List[Dict]:
    """
    Get matching rates for a service type
    
    Args:
        service_type: Type of service
        **filters: Filters to apply
        
    Returns:
        List of matching rates
    """
    
    try:
        if service_type == "Transport":
            calculator = TransportRateCalculationEngine()
            return calculator.get_matching_rates(**filters)
        else:
            # For other service types, implement basic search
            return frappe.get_all('Transport Rate', 
                                filters=filters,
                                fields=['*'])
            
    except Exception as e:
        frappe.log_error(f"Error getting matching rates: {str(e)}")
        return []


def validate_calculation_method(method: str, service_type: str = "Transport") -> bool:
    """
    Validate if a calculation method is available for a service type
    
    Args:
        method: Calculation method to validate
        service_type: Type of service
        
    Returns:
        True if method is valid, False otherwise
    """
    
    available_methods = get_available_methods(service_type)
    return method in available_methods


def get_calculation_engine(service_type: str = "Transport"):
    """
    Get the appropriate calculation engine for a service type
    
    Args:
        service_type: Type of service
        
    Returns:
        Calculation engine instance
    """
    
    if service_type == "Transport":
        return TransportRateCalculationEngine()
    else:
        # For other service types, return a basic engine
        return TransportRateCalculationEngine()


# Legacy function names for backward compatibility
def calculate_transport_rate(rate_data: Dict, **kwargs) -> Dict:
    """Legacy function for backward compatibility"""
    return calculate_rate(
        calculation_method=rate_data.get('calculation_method', 'Per Unit'),
        rate_value=rate_data.get('rate', 0),
        service_type="Transport",
        **rate_data,
        **kwargs
    )


def get_transport_rates(**filters) -> List[Dict]:
    """Legacy function for backward compatibility"""
    return get_matching_rates(service_type="Transport", **filters)
