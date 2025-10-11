# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from logistics.pricing_center.api_parts.calculation_engine import calculate_rate


class AirFreightRate(Document):
    def validate(self):
        self.validate_dates()
        self.validate_calculation_method()
    
    def validate_dates(self):
        """Validate rate validity dates."""
        if self.valid_to and self.valid_from and self.valid_to < self.valid_from:
            frappe.throw(_("Valid To date cannot be earlier than Valid From date"))
    
    def validate_calculation_method(self):
        """Validate calculation method is available for Air Freight."""
        from logistics.pricing_center.api_parts.calculation_engine import get_available_methods
        
        available_methods = get_available_methods("Air Freight")
        if self.calculation_method and self.calculation_method not in available_methods:
            frappe.throw(_("Calculation method '{0}' is not available for Air Freight").format(
                self.calculation_method
            ))
    
    def calculate_rate(self, **calculation_params):
        """Calculate rate using the configured calculation method."""
        if not self.calculation_method or not self.rate_value:
            return None
        
        try:
            result = calculate_rate(
                calculation_method=self.calculation_method,
                rate_value=self.rate_value,
                service_type="Air Freight",
                **calculation_params
            )
            return result
        except Exception as e:
            frappe.log_error(f"Air Freight rate calculation error: {str(e)}")
            frappe.throw(_("Error calculating Air Freight rate: {0}").format(str(e)))
    
    def get_rate_info(self):
        """Get rate information for display."""
        return {
            'rate_name': self.rate_name,
            'calculation_method': self.calculation_method,
            'rate_value': self.rate_value,
            'currency': self.currency,
            'origin_airport': self.origin_airport,
            'destination_airport': self.destination_airport,
            'airline': self.airline,
            'valid_from': self.valid_from,
            'valid_to': self.valid_to,
            'is_active': self.is_active
        }