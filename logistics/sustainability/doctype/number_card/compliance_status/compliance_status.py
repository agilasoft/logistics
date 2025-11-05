# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class ComplianceStatus(Document):
    def get_data(self):
        """Get compliance status data"""
        try:
            # Get count of compliant records
            compliant_count = frappe.db.sql("""
                SELECT COUNT(*) as total
                FROM `tabSustainability Compliance`
                WHERE status = 'Compliant'
            """, as_dict=True)
            
            # Get total compliance records
            total_count = frappe.db.sql("""
                SELECT COUNT(*) as total
                FROM `tabSustainability Compliance`
            """, as_dict=True)
            
            compliant = compliant_count[0].total or 0
            total = total_count[0].total or 0
            
            if total > 0:
                percentage = (compliant / total) * 100
                status_text = f"{compliant}/{total} ({percentage:.1f}%)"
            else:
                status_text = "No Records"
            
            return {
                "value": compliant,
                "formatted_value": status_text
            }
        except Exception as e:
            frappe.log_error(f"Error getting compliance status data: {e}", "Number Card Error")
            return {"value": 0, "formatted_value": "No Records"}
