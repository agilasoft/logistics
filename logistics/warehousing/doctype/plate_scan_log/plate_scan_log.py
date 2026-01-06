# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PlateScanLog(Document):
    """Document to log plate scanning activities for audit purposes"""
    
    def validate(self):
        """Validate the plate scan log entry"""
        if not self.plate_number:
            frappe.throw("Plate number is required")
        
        if not self.scan_result:
            frappe.throw("Scan result is required")
        
        # Clean plate number
        self.plate_number = self.clean_plate_number(self.plate_number)
    
    def clean_plate_number(self, plate_number):
        """Clean and standardize plate number"""
        import re
        if not plate_number:
            return None
        
        # Remove spaces and convert to uppercase
        cleaned = re.sub(r'\s+', '', str(plate_number).upper())
        return cleaned
    
    def before_save(self):
        """Actions before saving"""
        # Set scan time if not provided
        if not self.scan_time:
            from frappe.utils import now_datetime
            self.scan_time = now_datetime()

