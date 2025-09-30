# logistics/transport/doctype/transport_leg/transport_leg.py

import frappe
from frappe.model.document import Document


class TransportLeg(Document):
    def validate(self):
        """Update status based on start_date and end_date fields"""
        self.update_status()
    
    def update_status(self):
        """Update the status field based on start_date, end_date, run_sheet assignment, and sales_invoice"""
        if self.sales_invoice:
            # If sales_invoice is set, status should be "Billed" (highest priority)
            self.status = "Billed"
        elif self.end_date:
            # If end_date is set, status should be "Completed"
            self.status = "Completed"
        elif self.start_date:
            # If start_date is set but no end_date, status should be "Started"
            self.status = "Started"
        elif self.run_sheet:
            # If run_sheet is assigned but not started, status should be "Assigned"
            self.status = "Assigned"
        else:
            # If no run_sheet is assigned and no dates are set, status should be "Open"
            self.status = "Open"
    
    def before_save(self):
        """Ensure status is updated before saving"""
        self.update_status()


@frappe.whitelist()
def regenerate_routing(leg_name: str):
    """Regenerate routing for a Transport Leg"""
    from logistics.transport.routing import compute_leg_distance_time
    
    result = compute_leg_distance_time(leg_name)
    if result.get("ok", False):
        return {
            "distance_km": result.get("distance_km", 0),
            "duration_min": result.get("duration_min", 0),
            "provider": result.get("provider", "")
        }
    else:
        frappe.throw(result.get("msg", "Routing computation failed"))


@frappe.whitelist()
def regenerate_carbon(leg_name: str):
    """Regenerate carbon calculation for a Transport Leg"""
    from logistics.transport.carbon import compute_leg_carbon
    
    result = compute_leg_carbon(leg_name)
    if result.get("ok", False):
        return {
            "co2e_kg": result.get("co2e_kg", 0),
            "method": result.get("method", ""),
            "scope": result.get("scope", ""),
            "provider": result.get("provider", ""),
            "factor": result.get("factor", 0)
        }
    else:
        frappe.throw(result.get("msg", "Carbon computation failed"))