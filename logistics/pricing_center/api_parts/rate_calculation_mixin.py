# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from typing import Dict, List, Optional, Any
from logistics.pricing_center.api_parts.rate_calculation_engine import (
    rate_calculation_engine, 
    calculate_rate, 
    get_available_methods,
    validate_calculation_params
)


class RateCalculationMixin:
    """
    Mixin class that provides rate calculation capabilities to any DocType.
    
    Usage:
    class SalesQuote(Document, RateCalculationMixin):
        def calculate_line_rate(self, line):
            return self.calculate_rate_for_line(line)
    """
    
    def calculate_rate_for_line(self, line_data: Dict, **additional_params) -> Dict:
        """
        Calculate rate for a line item using the rate calculation engine.
        
        Args:
            line_data: Dictionary containing line data with calculation method and parameters
            **additional_params: Additional parameters to override or add
            
        Returns:
            Dict containing calculated rate information
        """
        # Extract calculation parameters from line data
        calculation_method = line_data.get('calculation_method')
        rate_value = line_data.get('rate_value', 0)
        
        if not calculation_method:
            frappe.throw(_("Calculation method is required for rate calculation"))
        
        if not rate_value:
            frappe.throw(_("Rate value is required for rate calculation"))
        
        # Prepare calculation parameters
        params = {
            'quantity': line_data.get('quantity', 0),
            'weight': line_data.get('weight', 0),
            'volume': line_data.get('volume', 0),
            'distance': line_data.get('distance', 0),
            'value': line_data.get('value', 0),
            'days': line_data.get('days', 0),
            'months': line_data.get('months', 0),
            'container_type': line_data.get('container_type'),
            'minimum_charge': line_data.get('minimum_charge', 0),
            'maximum_charge': line_data.get('maximum_charge', 0),
            'fixed_amount': line_data.get('fixed_amount', 0),
            'per_unit_rate': line_data.get('per_unit_rate', 0),
            'percentage_base': line_data.get('percentage_base', 0),
        }
        
        # Add any additional parameters
        params.update(additional_params)
        
        # Calculate the rate
        result = calculate_rate(calculation_method, rate_value, **params)
        
        # Add line-specific metadata
        result['line_id'] = line_data.get('name')
        result['line_description'] = line_data.get('description', '')
        
        return result
    
    def calculate_rates_for_table(self, table_field: str, **filters) -> List[Dict]:
        """
        Calculate rates for all rows in a child table.
        
        Args:
            table_field: Name of the child table field
            **filters: Optional filters to apply to table rows
            
        Returns:
            List of calculated rates for each row
        """
        table_data = getattr(self, table_field, [])
        results = []
        
        for row in table_data:
            # Apply filters if provided
            if filters:
                skip_row = False
                for key, value in filters.items():
                    if row.get(key) != value:
                        skip_row = True
                        break
                if skip_row:
                    continue
            
            # Calculate rate for this row
            try:
                result = self.calculate_rate_for_line(row)
                results.append(result)
            except Exception as e:
                frappe.log_error(f"Error calculating rate for row {row.get('name', 'unknown')}: {str(e)}")
                results.append({
                    'line_id': row.get('name'),
                    'error': str(e),
                    'amount': 0
                })
        
        return results
    
    def get_total_calculated_amount(self, table_field: str, **filters) -> float:
        """
        Get total calculated amount for a table.
        
        Args:
            table_field: Name of the child table field
            **filters: Optional filters to apply
            
        Returns:
            Total calculated amount
        """
        results = self.calculate_rates_for_table(table_field, **filters)
        return sum(result.get('amount', 0) for result in results if 'error' not in result)
    
    def validate_rate_calculation_data(self, line_data: Dict) -> bool:
        """
        Validate that line data has all required fields for rate calculation.
        
        Args:
            line_data: Dictionary containing line data
            
        Returns:
            True if valid, raises exception if invalid
        """
        required_fields = ['calculation_method', 'rate_value']
        missing_fields = [field for field in required_fields if not line_data.get(field)]
        
        if missing_fields:
            frappe.throw(_("Missing required fields for rate calculation: {0}").format(
                ', '.join(missing_fields)
            ))
        
        # Validate calculation parameters
        calculation_method = line_data.get('calculation_method')
        params = {k: v for k, v in line_data.items() if k not in ['calculation_method', 'rate_value']}
        
        try:
            validate_calculation_params(calculation_method, **params)
        except Exception as e:
            frappe.throw(_("Invalid calculation parameters: {0}").format(str(e)))
        
        return True
    
    def get_available_calculation_methods(self, service_type: str = None) -> List[str]:
        """
        Get available calculation methods for a service type.
        
        Args:
            service_type: Optional service type to filter methods
            
        Returns:
            List of available calculation methods
        """
        return get_available_methods(service_type)
    
    def auto_calculate_table_rates(self, table_field: str, amount_field: str = 'amount', **filters):
        """
        Automatically calculate and update rates for a table.
        
        Args:
            table_field: Name of the child table field
            amount_field: Name of the field to store calculated amount
            **filters: Optional filters to apply
        """
        table_data = getattr(self, table_field, [])
        
        for row in table_data:
            # Apply filters if provided
            if filters:
                skip_row = False
                for key, value in filters.items():
                    if row.get(key) != value:
                        skip_row = True
                        break
                if skip_row:
                    continue
            
            # Calculate and update rate
            try:
                result = self.calculate_rate_for_line(row)
                row.set(amount_field, result['amount'])
            except Exception as e:
                frappe.log_error(f"Error auto-calculating rate for row {row.get('name', 'unknown')}: {str(e)}")
                row.set(amount_field, 0)
    
    def get_rate_calculation_summary(self, table_field: str, **filters) -> Dict:
        """
        Get summary of rate calculations for a table.
        
        Args:
            table_field: Name of the child table field
            **filters: Optional filters to apply
            
        Returns:
            Dict containing calculation summary
        """
        results = self.calculate_rates_for_table(table_field, **filters)
        
        total_amount = sum(result.get('amount', 0) for result in results if 'error' not in result)
        error_count = sum(1 for result in results if 'error' in result)
        success_count = len(results) - error_count
        
        methods_used = list(set(result.get('method', '') for result in results if 'method' in result))
        
        return {
            'total_amount': total_amount,
            'total_lines': len(results),
            'successful_calculations': success_count,
            'errors': error_count,
            'methods_used': methods_used,
            'currency': getattr(self, 'currency', 'USD')
        }


class SalesQuoteRateCalculationMixin(RateCalculationMixin):
    """
    Specialized mixin for Sales Quote rate calculations.
    """
    
    def calculate_transport_rates(self) -> List[Dict]:
        """Calculate rates for transport lines."""
        return self.calculate_rates_for_table('transport_rates')
    
    def calculate_air_freight_rates(self) -> List[Dict]:
        """Calculate rates for air freight lines."""
        return self.calculate_rates_for_table('air_freight_rates')
    
    def calculate_sea_freight_rates(self) -> List[Dict]:
        """Calculate rates for sea freight lines."""
        return self.calculate_rates_for_table('sea_freight_rates')
    
    def calculate_customs_rates(self) -> List[Dict]:
        """Calculate rates for customs lines."""
        return self.calculate_rates_for_table('customs_rates')
    
    def calculate_warehousing_rates(self) -> List[Dict]:
        """Calculate rates for warehousing lines."""
        return self.calculate_rates_for_table('warehousing_rates')
    
    def get_total_quote_amount(self) -> float:
        """Get total amount for the entire quote."""
        total = 0
        total += self.get_total_calculated_amount('transport_rates')
        total += self.get_total_calculated_amount('air_freight_rates')
        total += self.get_total_calculated_amount('sea_freight_rates')
        total += self.get_total_calculated_amount('customs_rates')
        total += self.get_total_calculated_amount('warehousing_rates')
        return total


class CostRateCalculationMixin(RateCalculationMixin):
    """
    Specialized mixin for Cost rate calculations.
    """
    
    def calculate_cost_rates(self) -> List[Dict]:
        """Calculate rates for cost lines."""
        return self.calculate_rates_for_table('cost_lines')
    
    def get_total_cost_amount(self) -> float:
        """Get total cost amount."""
        return self.get_total_calculated_amount('cost_lines')


# Utility functions for easy integration
def add_rate_calculation_to_doctype(doctype_name: str, table_fields: List[str] = None):
    """
    Add rate calculation capabilities to any DocType.
    
    Args:
        doctype_name: Name of the DocType
        table_fields: List of table fields that contain rate data
    """
    # This would typically be done through hooks or custom code
    # For now, DocTypes can inherit from the mixin classes directly
    pass


def create_rate_calculation_field(field_name: str, label: str, **kwargs) -> Dict:
    """
    Create a standard rate calculation field configuration.
    
    Args:
        field_name: Name of the field
        label: Label for the field
        **kwargs: Additional field properties
        
    Returns:
        Dict containing field configuration
    """
    default_config = {
        'fieldtype': 'Currency',
        'label': label,
        'read_only': 1,
        'precision': 2
    }
    
    default_config.update(kwargs)
    return default_config

