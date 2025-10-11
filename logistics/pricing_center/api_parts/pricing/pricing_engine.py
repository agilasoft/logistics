import frappe
from frappe import _
from frappe.utils import flt

class PricingEngine:
    """Centralized pricing engine for all logistics services"""
    
    def __init__(self, sales_quote):
        self.sales_quote = sales_quote
        self.total_amount = 0
        self.currency = "USD"
    
    def calculate_total_quote_amount(self):
        """Calculate total amount for the entire sales quote"""
        
        try:
            total_amount = 0
            
            # Calculate transport amounts
            if self.sales_quote.transport_lanes:
                for lane in self.sales_quote.transport_lanes:
                    total_amount += flt(lane.total_amount or 0)
            
            # Calculate other service amounts (Air, Sea, Customs)
            # This can be extended for other services
            
            self.total_amount = total_amount
            return total_amount
            
        except Exception as e:
            frappe.log_error(f"Total quote calculation failed: {str(e)}")
            return 0
    
    def get_quote_summary(self):
        """Get comprehensive quote summary"""
        
        try:
            summary = {
                "total_amount": self.calculate_total_quote_amount(),
                "currency": self.currency,
                "transport_lanes": len(self.sales_quote.transport_lanes or []),
                "breakdown": self.get_breakdown()
            }
            
            return summary
            
        except Exception as e:
            frappe.log_error(f"Quote summary generation failed: {str(e)}")
            return {}
    
    def get_breakdown(self):
        """Get detailed breakdown of quote amounts"""
        
        breakdown = {
            "transport": {
                "lanes": [],
                "total": 0
            }
        }
        
        # Transport breakdown
        if self.sales_quote.transport_lanes:
            for lane in self.sales_quote.transport_lanes:
                lane_data = {
                    "origin": lane.origin,
                    "destination": lane.destination,
                    "vehicle_type": lane.vehicle_type,
                    "billing_method": lane.billing_method,
                    "amount": flt(lane.total_amount or 0)
                }
                breakdown["transport"]["lanes"].append(lane_data)
                breakdown["transport"]["total"] += flt(lane.total_amount or 0)
        
        return breakdown

@frappe.whitelist()
def calculate_total_quote_amount(sales_quote_name):
    """API endpoint for total quote calculation"""
    
    try:
        sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
        engine = PricingEngine(sales_quote)
        total_amount = engine.calculate_total_quote_amount()
        
        # Update the sales quote
        sales_quote.total_amount = total_amount
        sales_quote.save()
        frappe.db.commit()
        
        return total_amount
        
    except Exception as e:
        frappe.log_error(f"Total quote calculation API failed: {str(e)}")
        return 0

@frappe.whitelist()
def get_quote_summary(sales_quote_name):
    """API endpoint for quote summary"""
    
    try:
        sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
        engine = PricingEngine(sales_quote)
        summary = engine.get_quote_summary()
        
        return summary
        
    except Exception as e:
        frappe.log_error(f"Quote summary API failed: {str(e)}")
        return {}

