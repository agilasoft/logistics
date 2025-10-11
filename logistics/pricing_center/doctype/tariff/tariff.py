# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from logistics.pricing_center.api_parts.calculation_engine import get_available_methods


class Tariff(Document):
    def validate(self):
        self.validate_tariff_type()
        self.validate_dates()
        self.calculate_total_rates()
    
    def validate_tariff_type(self):
        """Validate tariff type and required fields."""
        if self.tariff_type == "Customer" and not self.customer:
            frappe.throw(_("Customer is required for Customer tariff"))
        
        if self.tariff_type == "Agent" and not self.agent:
            frappe.throw(_("Freight Agent is required for Agent tariff"))
    
    def validate_dates(self):
        """Validate tariff validity dates."""
        if self.valid_to and self.valid_from and self.valid_to < self.valid_from:
            frappe.throw(_("Valid To date cannot be earlier than Valid From date"))
    
    def calculate_total_rates(self):
        """Calculate total number of rates across all services."""
        total = 0
        
        # Count rates in each service
        if self.air_freight_rates:
            total += len(self.air_freight_rates)
        
        if self.sea_freight_rates:
            total += len(self.sea_freight_rates)
        
        if self.transport_rates:
            total += len(self.transport_rates)
        
        if self.warehouse_rates:
            total += len(self.warehouse_rates)
        
        if self.customs_rates:
            total += len(self.customs_rates)
        
        self.total_rates = total
    
    def get_available_calculators(self, service_type):
        """Get available calculation methods for a service type."""
        return get_available_methods(service_type)
    
    def get_rate_summary(self):
        """Get summary of all rates in this tariff."""
        summary = {
            'air_freight': len(self.air_freight_rates) if self.air_freight_rates else 0,
            'sea_freight': len(self.sea_freight_rates) if self.sea_freight_rates else 0,
            'transport': len(self.transport_rates) if self.transport_rates else 0,
            'warehouse': len(self.warehouse_rates) if self.warehouse_rates else 0,
            'customs': len(self.customs_rates) if self.customs_rates else 0,
            'total': self.total_rates
        }
        return summary


@frappe.whitelist()
def get_tariff_rates(tariff_name, service_type=None):
    """Get rates from a tariff, optionally filtered by service type."""
    tariff = frappe.get_doc("Tariff", tariff_name)
    
    if not tariff.is_active:
        frappe.throw(_("Tariff {0} is not active").format(tariff_name))
    
    rates = []
    
    if service_type == "Air Freight" or not service_type:
        if tariff.air_freight_rates:
            for rate in tariff.air_freight_rates:
                rates.append({
                    'service_type': 'Air Freight',
                    'rate_name': rate.rate_name,
                    'calculation_method': rate.calculation_method,
                    'rate_value': rate.rate_value,
                    'currency': rate.currency,
                    'valid_from': rate.valid_from,
                    'valid_to': rate.valid_to
                })
    
    if service_type == "Sea Freight" or not service_type:
        if tariff.sea_freight_rates:
            for rate in tariff.sea_freight_rates:
                rates.append({
                    'service_type': 'Sea Freight',
                    'rate_name': rate.rate_name,
                    'calculation_method': rate.calculation_method,
                    'rate_value': rate.rate_value,
                    'currency': rate.currency,
                    'valid_from': rate.valid_from,
                    'valid_to': rate.valid_to
                })
    
    if service_type == "Transport" or not service_type:
        if tariff.transport_rates:
            for rate in tariff.transport_rates:
                rates.append({
                    'service_type': 'Transport',
                    'rate_name': rate.rate_name,
                    'calculation_method': rate.calculation_method,
                    'rate_value': rate.rate_value,
                    'currency': rate.currency,
                    'valid_from': rate.valid_from,
                    'valid_to': rate.valid_to
                })
    
    if service_type == "Warehousing" or not service_type:
        if tariff.warehouse_rates:
            for rate in tariff.warehouse_rates:
                rates.append({
                    'service_type': 'Warehousing',
                    'rate_name': rate.rate_name,
                    'calculation_method': rate.calculation_method,
                    'rate_value': rate.rate_value,
                    'currency': rate.currency,
                    'valid_from': rate.valid_from,
                    'valid_to': rate.valid_to
                })
    
    if service_type == "Customs" or not service_type:
        if tariff.customs_rates:
            for rate in tariff.customs_rates:
                rates.append({
                    'service_type': 'Customs',
                    'rate_name': rate.rate_name,
                    'calculation_method': rate.calculation_method,
                    'rate_value': rate.rate_value,
                    'currency': rate.currency,
                    'valid_from': rate.valid_from,
                    'valid_to': rate.valid_to
                })
    
    return rates


@frappe.whitelist()
def get_available_calculators(service_type):
    """Get available calculation methods for a service type."""
    return get_available_methods(service_type)


@frappe.whitelist()
def get_tariff_summary(tariff_name):
    """Get summary of a tariff including rate counts and details."""
    try:
        tariff = frappe.get_doc("Tariff", tariff_name)
        
        if not tariff.is_active:
            return {"status": "error", "message": "Tariff is not active"}
        
        summary = {
            "tariff_name": tariff.tariff_name,
            "tariff_type": tariff.tariff_type,
            "customer": tariff.customer if tariff.tariff_type == "Customer" else None,
            "agent": tariff.agent if tariff.tariff_type == "Agent" else None,
            "currency": tariff.currency,
            "valid_from": tariff.valid_from,
            "valid_to": tariff.valid_to,
            "is_active": tariff.is_active,
            "total_rates": tariff.total_rates,
            "rate_breakdown": {
                "air_freight": len(tariff.air_freight_rates) if tariff.air_freight_rates else 0,
                "sea_freight": len(tariff.sea_freight_rates) if tariff.sea_freight_rates else 0,
                "transport": len(tariff.transport_rates) if tariff.transport_rates else 0,
                "warehouse": len(tariff.warehouse_rates) if tariff.warehouse_rates else 0,
                "customs": len(tariff.customs_rates) if tariff.customs_rates else 0
            },
            "service_details": {
                "air_freight": [{"rate_name": rate.rate_name, "calculation_method": rate.calculation_method, "rate_value": rate.rate_value} for rate in tariff.air_freight_rates] if tariff.air_freight_rates else [],
                "sea_freight": [{"rate_name": rate.rate_name, "calculation_method": rate.calculation_method, "rate_value": rate.rate_value} for rate in tariff.sea_freight_rates] if tariff.sea_freight_rates else [],
                "transport": [{"rate_name": rate.rate_name, "calculation_method": rate.calculation_method, "rate_value": rate.rate_value} for rate in tariff.transport_rates] if tariff.transport_rates else [],
                "warehouse": [{"rate_name": rate.rate_name, "calculation_method": rate.calculation_method, "rate_value": rate.rate_value} for rate in tariff.warehouse_rates] if tariff.warehouse_rates else [],
                "customs": [{"rate_name": rate.rate_name, "calculation_method": rate.calculation_method, "rate_value": rate.rate_value} for rate in tariff.customs_rates] if tariff.customs_rates else []
            }
        }
        
        return {"status": "success", "data": summary}
        
    except Exception as e:
        frappe.log_error(f"Tariff summary error: {str(e)}")
        return {"status": "error", "message": str(e)}