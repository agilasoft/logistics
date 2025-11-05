# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class ActiveGoals(Document):
    def get_data(self):
        """Get active goals count"""
        try:
            # Get count of active sustainability goals
            active_goals = frappe.db.sql("""
                SELECT COUNT(*) as total
                FROM `tabSustainability Goals`
                WHERE status = 'Active'
            """, as_dict=True)
            
            return {
                "value": active_goals[0].total or 0,
                "formatted_value": f"{active_goals[0].total or 0} Goals"
            }
        except Exception as e:
            frappe.log_error(f"Error getting active goals data: {e}", "Number Card Error")
            return {"value": 0, "formatted_value": "0 Goals"}
