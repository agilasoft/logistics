# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from logistics.pricing_center.api_parts.calculation_engine import calculate_rate


class WarehouseRate(Document):
    def validate(self):
        self.validate_dates()
        self.validate_calculation_method()
    
    def validate_dates(self):
        """Validate rate validity dates."""
        if self.valid_to and self.valid_from and self.valid_to < self.valid_from:
            frappe.throw(_("Valid To date cannot be earlier than Valid From date"))
    
    def validate_calculation_method(self):
        """Validate calculation method is available for Warehousing."""
        from logistics.pricing_center.api_parts.calculation_engine import get_available_methods
        
        available_methods = get_available_methods("Warehousing")
        if self.calculation_method and self.calculation_method not in available_methods:
            frappe.throw(_("Calculation method '{0}' is not available for Warehousing").format(
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
                service_type="Warehousing",
                **calculation_params
            )
            return result
        except Exception as e:
            frappe.log_error(f"Warehouse rate calculation error: {str(e)}")
            frappe.throw(_("Error calculating Warehouse rate: {0}").format(str(e)))
    
    def get_rate_info(self):
        """Get rate information for display."""
        return {
            'rate_name': self.rate_name,
            'calculation_method': self.calculation_method,
            'rate_value': self.rate_value,
            'currency': self.currency,
            'warehouse': self.warehouse,
            'storage_type': self.storage_type,
            'handling_type': self.handling_type,
            'valid_from': self.valid_from,
            'valid_to': self.valid_to,
            'is_active': self.is_active
        }

