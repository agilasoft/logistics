# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class SustainabilityOverview(Document):
    def get_data(self):
        """Get sustainability overview chart data"""
        try:
            # Get carbon footprint data by month
            carbon_data = frappe.db.sql("""
                SELECT 
                    DATE_FORMAT(date, '%Y-%m') as month,
                    SUM(total_emissions) as total_emissions
                FROM `tabCarbon Footprint`
                WHERE docstatus != 2
                AND date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
                GROUP BY DATE_FORMAT(date, '%Y-%m')
                ORDER BY month
            """, as_dict=True)
            
            # Get energy consumption data by month
            energy_data = frappe.db.sql("""
                SELECT 
                    DATE_FORMAT(date, '%Y-%m') as month,
                    SUM(consumption_value) as total_consumption
                FROM `tabEnergy Consumption`
                WHERE docstatus != 2
                AND date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
                GROUP BY DATE_FORMAT(date, '%Y-%m')
                ORDER BY month
            """, as_dict=True)
            
            # Prepare chart data
            months = []
            carbon_values = []
            energy_values = []
            
            # Create a complete month list for the last 12 months
            from datetime import datetime, timedelta
            current_date = datetime.now()
            for i in range(12):
                month_date = current_date - timedelta(days=30*i)
                month_str = month_date.strftime('%Y-%m')
                months.append(month_date.strftime('%b %Y'))
                
                # Find corresponding data
                carbon_val = next((d.total_emissions for d in carbon_data if d.month == month_str), 0)
                energy_val = next((d.total_consumption for d in energy_data if d.month == month_str), 0)
                
                carbon_values.append(carbon_val or 0)
                energy_values.append(energy_val or 0)
            
            # Reverse to show oldest to newest
            months.reverse()
            carbon_values.reverse()
            energy_values.reverse()
            
            return {
                "labels": months,
                "datasets": [
                    {
                        "name": "Carbon Footprint (kg CO2e)",
                        "values": carbon_values
                    },
                    {
                        "name": "Energy Consumption (kWh)",
                        "values": energy_values
                    }
                ]
            }
            
        except Exception as e:
            frappe.log_error(f"Error getting sustainability overview data: {e}", "Chart Error")
            return {
                "labels": [],
                "datasets": []
            }
