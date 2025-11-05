# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import flt
from frappe import _

class SeaShipment(Document):
    def before_save(self):
        """Calculate sustainability metrics before saving"""
        self.calculate_sustainability_metrics()
    
    def after_submit(self):
        """Record sustainability metrics after shipment submission"""
        self.record_sustainability_metrics()
    
    def calculate_sustainability_metrics(self):
        """Calculate sustainability metrics for this sea shipment"""
        try:
            # Calculate carbon footprint based on weight and distance
            if hasattr(self, 'weight') and hasattr(self, 'origin_port') and hasattr(self, 'destination_port'):
                # Get distance between ports (simplified calculation)
                distance = self._calculate_port_distance(self.origin_port, self.destination_port)
                if distance and self.weight:
                    # Use sea freight emission factor
                    emission_factor = 0.01  # kg CO2e per ton-km for sea freight
                    carbon_footprint = (flt(self.weight) / 1000) * distance * emission_factor
                    self.estimated_carbon_footprint = carbon_footprint
                    
                    # Calculate fuel consumption estimate
                    fuel_consumption = self._calculate_fuel_consumption(distance, flt(self.weight))
                    self.estimated_fuel_consumption = fuel_consumption
                
        except Exception as e:
            frappe.log_error(f"Error calculating sustainability metrics for Sea Shipment {self.name}: {e}", "Sea Shipment Sustainability Error")
    
    def record_sustainability_metrics(self):
        """Record sustainability metrics in the centralized system"""
        try:
            from logistics.sustainability.utils.sustainability_integration import integrate_sustainability
            
            result = integrate_sustainability(
                doctype=self.doctype,
                docname=self.name,
                module="Sea Freight",
                doc=self
            )
            
            if result.get("status") == "success":
                frappe.msgprint(_("Sustainability metrics recorded successfully"))
            elif result.get("status") == "skipped":
                # Don't show message if sustainability is not enabled
                pass
            else:
                frappe.log_error(f"Sustainability recording failed: {result.get('message', 'Unknown error')}", "Sea Shipment Sustainability Error")
                
        except Exception as e:
            frappe.log_error(f"Error recording sustainability metrics for Sea Shipment {self.name}: {e}", "Sea Shipment Sustainability Error")
    
    def _calculate_port_distance(self, origin: str, destination: str) -> float:
        """Calculate distance between ports (simplified)"""
        # This would typically use a geocoding service or database
        # For now, return a default distance based on common sea routes
        route_distances = {
            ("LAX", "SIN"): 8500,  # Los Angeles to Singapore
            ("HKG", "LAX"): 12000,  # Hong Kong to Los Angeles
            ("ROT", "NYC"): 5800,  # Rotterdam to New York
            ("SIN", "HKG"): 2600,  # Singapore to Hong Kong
        }
        
        # Try to find exact match
        key = (origin, destination)
        if key in route_distances:
            return route_distances[key]
        
        # Try reverse match
        key = (destination, origin)
        if key in route_distances:
            return route_distances[key]
        
        # Default distance for sea freight
        return 5000.0  # Default 5000 km
    
    def _calculate_fuel_consumption(self, distance: float, weight: float) -> float:
        """Calculate estimated fuel consumption for sea freight"""
        # Sea freight fuel consumption is typically 0.1-0.2 L per 100 km per ton
        fuel_rate = 0.15  # L per 100 km per ton
        return (fuel_rate * distance * (weight / 1000)) / 100.0
    
import frappe

@frappe.whitelist()
def create_sales_invoice(booking_name, posting_date, customer, tax_category=None, invoice_type=None):
    booking = frappe.get_doc('Sea Freight Booking', booking_name)

    # Fetch naming series from the Invoice Type doctype
    naming_series = None
    if invoice_type:
        naming_series = frappe.db.get_value("Invoice Type", invoice_type, "naming_series")

    invoice = frappe.new_doc('Sales Invoice')
    invoice.customer = customer
    invoice.posting_date = posting_date
    invoice.tax_category = tax_category or None
    invoice.naming_series = naming_series or None
    invoice.invoice_type = invoice_type or None  # Optional: standard field if exists
    invoice.custom_invoice_type = invoice_type or None  # Custom field explicitly filled
    invoice.job_costing_number = booking_name  # Optional: link to booking

    for charge in booking.charges:
        if charge.bill_to == customer and charge.invoice_type == invoice_type:
            invoice.append('items', {
                'item_code': charge.charge_item,
                'item_name': charge.charge_name or charge.charge_item,
                'description': charge.charge_description,
                'qty': 1,
                'rate': charge.selling_amount or 0,
                'currency': charge.selling_currency,
                'item_tax_template': charge.item_tax_template or None
            })

    if not invoice.items:
        frappe.throw("No matching charges found for the selected customer and invoice type.")

    invoice.set_missing_values()
    invoice.insert(ignore_permissions=True)
    return invoice

@frappe.whitelist()
def compute_chargeable(self):
    weight = self.weight or 0
    volume = self.volume or 0

    # Use direction to determine conversion factor
    if self.direction == "Domestic":
        volume_weight = volume * 333  # Philippine domestic standard
    else:
        volume_weight = volume * 1000  # International standard

    self.chargeable = max(weight, volume_weight)
