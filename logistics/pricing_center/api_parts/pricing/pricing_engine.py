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
        """Calculate total amount for the entire sales quote (all modes: Transport, Air, Sea, Customs, Warehousing)"""
        try:
            total_amount = 0

            # Transport
            if getattr(self.sales_quote, "transport_lanes", None):
                for lane in self.sales_quote.transport_lanes:
                    total_amount += flt(lane.total_amount or 0)
            if getattr(self.sales_quote, "transport", None):
                for row in self.sales_quote.transport:
                    total_amount += flt(getattr(row, "estimated_revenue", 0) or getattr(row, "total_amount", 0) or 0)

            # Air Freight
            if getattr(self.sales_quote, "air_freight", None):
                for row in self.sales_quote.air_freight:
                    total_amount += flt(getattr(row, "estimated_revenue", 0) or getattr(row, "base_amount", 0) or 0)

            # Sea Freight
            if getattr(self.sales_quote, "sea_freight", None):
                for row in self.sales_quote.sea_freight:
                    total_amount += flt(getattr(row, "estimated_revenue", 0) or getattr(row, "base_amount", 0) or 0)

            # Customs
            if getattr(self.sales_quote, "customs", None):
                for row in self.sales_quote.customs:
                    total_amount += flt(getattr(row, "estimated_revenue", 0) or getattr(row, "base_amount", 0) or 0)

            # Warehousing
            if getattr(self.sales_quote, "warehousing", None):
                for row in self.sales_quote.warehousing:
                    total_amount += flt(getattr(row, "estimated_revenue", 0) or getattr(row, "base_amount", 0) or 0)

            self.total_amount = total_amount
            return total_amount

        except Exception as e:
            frappe.log_error(f"Total quote calculation failed: {str(e)}")
            return 0
    
    def get_quote_summary(self):
        """Get comprehensive quote summary"""
        
        try:
            bd = self.get_breakdown()
            summary = {
                "total_amount": self.calculate_total_quote_amount(),
                "currency": self.currency,
                "transport_lanes": len(getattr(self.sales_quote, "transport_lanes", None) or []),
                "breakdown": bd
            }
            
            return summary
            
        except Exception as e:
            frappe.log_error(f"Quote summary generation failed: {str(e)}")
            return {}
    
    def get_breakdown(self):
        """Get detailed breakdown of quote amounts by mode"""
        breakdown = {
            "transport": {"lanes": [], "rows": [], "total": 0},
            "air_freight": {"rows": [], "total": 0},
            "sea_freight": {"rows": [], "total": 0},
            "customs": {"rows": [], "total": 0},
            "warehousing": {"rows": [], "total": 0},
        }

        # Transport lanes
        if getattr(self.sales_quote, "transport_lanes", None):
            for lane in self.sales_quote.transport_lanes:
                amt = flt(lane.total_amount or 0)
                breakdown["transport"]["lanes"].append({
                    "origin": getattr(lane, "origin", ""),
                    "destination": getattr(lane, "destination", ""),
                    "vehicle_type": getattr(lane, "vehicle_type", ""),
                    "billing_method": getattr(lane, "billing_method", ""),
                    "amount": amt
                })
                breakdown["transport"]["total"] += amt

        # Transport rows
        if getattr(self.sales_quote, "transport", None):
            for row in self.sales_quote.transport:
                amt = flt(getattr(row, "estimated_revenue", 0) or getattr(row, "total_amount", 0) or 0)
                breakdown["transport"]["rows"].append({"amount": amt})
                breakdown["transport"]["total"] += amt

        # Air Freight
        if getattr(self.sales_quote, "air_freight", None):
            for row in self.sales_quote.air_freight:
                amt = flt(getattr(row, "estimated_revenue", 0) or getattr(row, "base_amount", 0) or 0)
                breakdown["air_freight"]["rows"].append({"amount": amt})
                breakdown["air_freight"]["total"] += amt

        # Sea Freight
        if getattr(self.sales_quote, "sea_freight", None):
            for row in self.sales_quote.sea_freight:
                amt = flt(getattr(row, "estimated_revenue", 0) or getattr(row, "base_amount", 0) or 0)
                breakdown["sea_freight"]["rows"].append({"amount": amt})
                breakdown["sea_freight"]["total"] += amt

        # Customs
        if getattr(self.sales_quote, "customs", None):
            for row in self.sales_quote.customs:
                amt = flt(getattr(row, "estimated_revenue", 0) or getattr(row, "base_amount", 0) or 0)
                breakdown["customs"]["rows"].append({"amount": amt})
                breakdown["customs"]["total"] += amt

        # Warehousing
        if getattr(self.sales_quote, "warehousing", None):
            for row in self.sales_quote.warehousing:
                amt = flt(getattr(row, "estimated_revenue", 0) or getattr(row, "base_amount", 0) or 0)
                breakdown["warehousing"]["rows"].append({"amount": amt})
                breakdown["warehousing"]["total"] += amt

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

