# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class TotalEnergyConsumption(Document):
    def get_data(self):
        """Get total energy consumption data"""
        try:
            # Get total energy consumption from Energy Consumption DocType
            total_consumption = frappe.db.sql("""
                SELECT SUM(consumption_value) as total
                FROM `tabEnergy Consumption`
                WHERE docstatus != 2
            """, as_dict=True)
            
            return {
                "value": total_consumption[0].total or 0,
                "formatted_value": f"{total_consumption[0].total or 0:.2f} kWh"
            }
        except Exception as e:
            frappe.log_error(f"Error getting energy consumption data: {e}", "Number Card Error")
            return {"value": 0, "formatted_value": "0 kWh"}
