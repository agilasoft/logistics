# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, today
from typing import Dict, List, Optional
import json

from logistics.pricing_center.api_parts.transport_rate_calculation_engine import (
    TransportRateCalculationEngine,
    calculate_transport_rate_for_quote,
    get_transport_rates_for_route,
    calculate_bulk_transport_rates
)


class SalesQuoteTransportIntegration:
    """
    Sales Quote Integration for Transport Rate Calculations
    
    This class provides easy integration between Sales Quote and Transport Rate calculations.
    It handles the communication between Sales Quote and the Transport Rate calculation engine.
    """
    
    def __init__(self, sales_quote_doc):
        self.doc = sales_quote_doc
        self.calculator = TransportRateCalculationEngine()
    
    def calculate_transport_line_rate(self, transport_line) -> Dict:
        """
        Calculate rate for a single transport line in Sales Quote
        
        Args:
            transport_line: Transport line document from Sales Quote
            
        Returns:
            Calculation result
        """
        
        try:
            # Get rate data from transport line
            rate_data = self._extract_rate_data_from_line(transport_line)
            
            # Get actual data for calculation
            actual_data = self._extract_actual_data_from_line(transport_line)
            
            # Calculate rate
            result = self.calculator.calculate_transport_rate(
                rate_data=rate_data,
                **actual_data
            )
            
            return result
            
        except Exception as e:
            frappe.log_error(f"Transport line calculation error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'amount': 0
            }
    
    def calculate_all_transport_rates(self) -> Dict:
        """
        Calculate rates for all transport lines in the Sales Quote
        
        Returns:
            Summary of all calculations
        """
        
        results = {
            'lines': [],
            'total_amount': 0,
            'successful_calculations': 0,
            'failed_calculations': 0,
            'errors': []
        }
        
        if not hasattr(self.doc, 'transport_rates') or not self.doc.transport_rates:
            return results
        
        for line in self.doc.transport_rates:
            line_result = self.calculate_transport_line_rate(line)
            
            # Update line with calculated amount
            if line_result.get('success'):
                line.rate = line_result.get('amount', 0)
                line.total_amount = line.rate * flt(line.quantity or 1)
                results['total_amount'] += line.total_amount
                results['successful_calculations'] += 1
            else:
                results['failed_calculations'] += 1
                results['errors'].append({
                    'line': line.idx,
                    'error': line_result.get('error', 'Unknown error')
                })
            
            results['lines'].append({
                'line_idx': line.idx,
                'item_code': line.item_code,
                'item_name': line.item_name,
                'result': line_result
            })
        
        return results
    
    def auto_calculate_transport_rates(self):
        """
        Automatically calculate and update all transport rates in the Sales Quote
        """
        
        try:
            results = self.calculate_all_transport_rates()
            
            # Update grand total if transport rates exist
            if hasattr(self.doc, 'transport_rates') and self.doc.transport_rates:
                self._update_grand_total()
            
            # Save the document
            self.doc.save()
            frappe.db.commit()
            
            return {
                'success': True,
                'message': f"Calculated {results['successful_calculations']} transport rates successfully",
                'total_amount': results['total_amount'],
                'errors': results['errors']
            }
            
        except Exception as e:
            frappe.log_error(f"Auto calculate transport rates error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_available_rates_for_route(self, 
                                     origin: str = None,
                                     destination: str = None,
                                     vehicle_type: str = None,
                                     load_type: str = None,
                                     container_type: str = None,
                                     tariff_name: str = None) -> List[Dict]:
        """
        Get available transport rates for a specific route
        
        Args:
            origin: Origin location
            destination: Destination location
            vehicle_type: Vehicle type
            load_type: Load type
            container_type: Container type
            tariff_name: Specific tariff to use
            
        Returns:
            List of available rates
        """
        
        try:
            rates = self.calculator.get_matching_rates(
                origin_location=origin,
                destination_location=destination,
                vehicle_type=vehicle_type,
                load_type=load_type,
                container_type=container_type,
                tariff_name=tariff_name
            )
            
            return rates
            
        except Exception as e:
            frappe.log_error(f"Get available rates error: {str(e)}")
            return []
    
    def add_transport_line_from_rate(self, 
                                   rate_data: Dict,
                                   quantity: float = 1,
                                   **actual_data) -> Dict:
        """
        Add a new transport line to Sales Quote based on rate configuration
        
        Args:
            rate_data: Rate configuration
            quantity: Quantity for the line
            **actual_data: Actual data for calculation
            
        Returns:
            Result of adding the line
        """
        
        try:
            # Calculate rate
            calculation_result = self.calculator.calculate_transport_rate(
                rate_data=rate_data,
                **actual_data
            )
            
            if not calculation_result.get('success'):
                return {
                    'success': False,
                    'error': calculation_result.get('error', 'Calculation failed')
                }
            
            # Create new transport line
            new_line = self.doc.append('transport_rates', {
                'item_code': rate_data.get('item_code'),
                'item_name': rate_data.get('item_name'),
                'quantity': quantity,
                'rate': calculation_result.get('amount', 0),
                'total_amount': calculation_result.get('amount', 0) * quantity,
                'currency': rate_data.get('currency', 'USD'),
                'calculation_method': rate_data.get('calculation_method'),
                'unit_type': rate_data.get('unit_type'),
                'vehicle_type': rate_data.get('vehicle_type'),
                'load_type': rate_data.get('load_type'),
                'container_type': rate_data.get('container_type'),
                'location_from': rate_data.get('location_from'),
                'location_to': rate_data.get('location_to')
            })
            
            return {
                'success': True,
                'line': new_line,
                'calculation_result': calculation_result
            }
            
        except Exception as e:
            frappe.log_error(f"Add transport line error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_rate_data_from_line(self, transport_line) -> Dict:
        """Extract rate data from transport line"""
        
        return {
            'item_code': transport_line.item_code,
            'item_name': transport_line.item_name,
            'calculation_method': getattr(transport_line, 'calculation_method', 'Per Unit'),
            'rate': transport_line.rate,
            'currency': getattr(transport_line, 'currency', 'USD'),
            'unit_type': getattr(transport_line, 'unit_type', 'Weight'),
            'minimum_charge': getattr(transport_line, 'minimum_charge', 0),
            'maximum_charge': getattr(transport_line, 'maximum_charge', 0),
            'base_amount': getattr(transport_line, 'base_amount', 0),
            'minimum_quantity': getattr(transport_line, 'minimum_quantity', 0),
            'vehicle_type': getattr(transport_line, 'vehicle_type', None),
            'load_type': getattr(transport_line, 'load_type', None),
            'container_type': getattr(transport_line, 'container_type', None),
            'location_from': getattr(transport_line, 'location_from', None),
            'location_to': getattr(transport_line, 'location_to', None)
        }
    
    def _extract_actual_data_from_line(self, transport_line) -> Dict:
        """Extract actual data for calculation from transport line"""
        
        return {
            'actual_quantity': flt(transport_line.quantity or 1),
            'actual_weight': flt(getattr(transport_line, 'actual_weight', 0)),
            'actual_volume': flt(getattr(transport_line, 'actual_volume', 0)),
            'actual_distance': flt(getattr(transport_line, 'actual_distance', 0)),
            'actual_pieces': cint(getattr(transport_line, 'actual_pieces', 0))
        }
    
    def _update_grand_total(self):
        """Update grand total of Sales Quote"""
        
        if hasattr(self.doc, 'grand_total'):
            # Calculate total from all service types
            total = 0
            
            # Transport rates
            if hasattr(self.doc, 'transport_rates') and self.doc.transport_rates:
                for line in self.doc.transport_rates:
                    total += flt(line.total_amount or 0)
            
            # Air freight rates
            if hasattr(self.doc, 'air_freight_rates') and self.doc.air_freight_rates:
                for line in self.doc.air_freight_rates:
                    total += flt(line.total_amount or 0)
            
            # Sea freight rates
            if hasattr(self.doc, 'sea_freight_rates') and self.doc.sea_freight_rates:
                for line in self.doc.sea_freight_rates:
                    total += flt(line.total_amount or 0)
            
            # Customs rates
            if hasattr(self.doc, 'customs_rates') and self.doc.customs_rates:
                for line in self.doc.customs_rates:
                    total += flt(line.total_amount or 0)
            
            # Warehousing rates
            if hasattr(self.doc, 'warehousing_rates') and self.doc.warehousing_rates:
                for line in self.doc.warehousing_rates:
                    total += flt(line.total_amount or 0)
            
            self.doc.grand_total = total


# API Functions for Sales Quote Integration

@frappe.whitelist()
def calculate_sales_quote_transport_rates(sales_quote_name: str) -> Dict:
    """
    API endpoint to calculate all transport rates for a Sales Quote
    
    Args:
        sales_quote_name: Name of the Sales Quote
        
    Returns:
        Calculation results
    """
    
    try:
        # Get Sales Quote document
        sales_quote_doc = frappe.get_doc('Sales Quote', sales_quote_name)
        
        # Initialize integration
        integration = SalesQuoteTransportIntegration(sales_quote_doc)
        
        # Calculate rates
        result = integration.auto_calculate_transport_rates()
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Sales Quote transport rate calculation error: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@frappe.whitelist()
def get_transport_rates_for_sales_quote(sales_quote_name: str,
                                       origin: str = None,
                                       destination: str = None,
                                       vehicle_type: str = None,
                                       load_type: str = None,
                                       container_type: str = None,
                                       tariff_name: str = None) -> List[Dict]:
    """
    API endpoint to get available transport rates for Sales Quote
    
    Args:
        sales_quote_name: Name of the Sales Quote
        origin: Origin location
        destination: Destination location
        vehicle_type: Vehicle type
        load_type: Load type
        container_type: Container type
        tariff_name: Specific tariff
        
    Returns:
        List of available rates
    """
    
    try:
        # Get Sales Quote document
        sales_quote_doc = frappe.get_doc('Sales Quote', sales_quote_name)
        
        # Initialize integration
        integration = SalesQuoteTransportIntegration(sales_quote_doc)
        
        # Get available rates
        rates = integration.get_available_rates_for_route(
            origin=origin,
            destination=destination,
            vehicle_type=vehicle_type,
            load_type=load_type,
            container_type=container_type,
            tariff_name=tariff_name
        )
        
        return rates
        
    except Exception as e:
        frappe.log_error(f"Get transport rates for Sales Quote error: {str(e)}")
        return []


@frappe.whitelist()
def add_transport_line_to_sales_quote(sales_quote_name: str,
                                    rate_data: str,
                                    quantity: float = 1,
                                    **actual_data) -> Dict:
    """
    API endpoint to add transport line to Sales Quote
    
    Args:
        sales_quote_name: Name of the Sales Quote
        rate_data: JSON string of rate configuration
        quantity: Quantity for the line
        **actual_data: Actual data for calculation
        
    Returns:
        Result of adding the line
    """
    
    try:
        # Parse rate data
        if isinstance(rate_data, str):
            rate_config = json.loads(rate_data)
        else:
            rate_config = rate_data
        
        # Get Sales Quote document
        sales_quote_doc = frappe.get_doc('Sales Quote', sales_quote_name)
        
        # Initialize integration
        integration = SalesQuoteTransportIntegration(sales_quote_doc)
        
        # Add transport line
        result = integration.add_transport_line_from_rate(
            rate_data=rate_config,
            quantity=quantity,
            **actual_data
        )
        
        if result.get('success'):
            # Save the document
            sales_quote_doc.save()
            frappe.db.commit()
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Add transport line to Sales Quote error: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@frappe.whitelist()
def calculate_single_transport_line(sales_quote_name: str, line_idx: int) -> Dict:
    """
    API endpoint to calculate rate for a single transport line
    
    Args:
        sales_quote_name: Name of the Sales Quote
        line_idx: Index of the transport line
        
    Returns:
        Calculation result
    """
    
    try:
        # Get Sales Quote document
        sales_quote_doc = frappe.get_doc('Sales Quote', sales_quote_name)
        
        # Find the transport line
        transport_line = None
        if hasattr(sales_quote_doc, 'transport_rates') and sales_quote_doc.transport_rates:
            for line in sales_quote_doc.transport_rates:
                if line.idx == line_idx:
                    transport_line = line
                    break
        
        if not transport_line:
            return {
                'success': False,
                'error': f'Transport line with index {line_idx} not found'
            }
        
        # Initialize integration
        integration = SalesQuoteTransportIntegration(sales_quote_doc)
        
        # Calculate rate
        result = integration.calculate_transport_line_rate(transport_line)
        
        if result.get('success'):
            # Update the line
            transport_line.rate = result.get('amount', 0)
            transport_line.total_amount = transport_line.rate * flt(transport_line.quantity or 1)
            
            # Save the document
            sales_quote_doc.save()
            frappe.db.commit()
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Calculate single transport line error: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }





