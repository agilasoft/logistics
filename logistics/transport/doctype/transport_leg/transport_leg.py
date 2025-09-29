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