# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class TotalCarbonFootprint(Document):
    def get_data(self):
        """Get total carbon footprint data"""
        try:
            # Get total carbon footprint from Carbon Footprint DocType
            total_emissions = frappe.db.sql("""
                SELECT SUM(total_emissions) as total
                FROM `tabCarbon Footprint`
                WHERE docstatus != 2
            """, as_dict=True)
            
            return {
                "value": total_emissions[0].total or 0,
                "formatted_value": f"{total_emissions[0].total or 0:.2f} kg CO2e"
            }
        except Exception as e:
            frappe.log_error(f"Error getting carbon footprint data: {e}", "Number Card Error")
            return {"value": 0, "formatted_value": "0 kg CO2e"}
