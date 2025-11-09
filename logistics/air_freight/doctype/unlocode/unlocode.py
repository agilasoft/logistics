"""
UNLOCO DocType
Auto-populate UNLOCO details when creating new records
"""

import frappe
from frappe import _
from frappe.model.document import Document

class UNLOCO(Document):
    def validate(self):
        """Validate UNLOCO document"""
        # Validate UNLOCO code format
        if self.unlocode and len(self.unlocode) != 5:
            frappe.throw(_("UNLOCO code must be exactly 5 characters long"))
        
        # Auto-populate details if enabled
        if self.auto_populate and self.unlocode:
            self.populate_unlocode_details()
    
    def populate_unlocode_details(self):
        """Populate UNLOCO details from database or external sources"""
        try:
            from logistics.air_freight.utils.unlocode_utils import populate_unlocode_details
            
            # Get UNLOCO details
            details = populate_unlocode_details(self.unlocode)
            
            if details:
                # Update document with populated details
                for field_name, field_value in details.items():
                    if hasattr(self, field_name) and field_value is not None:
                        setattr(self, field_name, field_value)
                
                # Update last updated timestamp
                self.last_updated = frappe.utils.now()
                
        except Exception as e:
            frappe.log_error(f"UNLOCO details population error: {str(e)}")
    
    def before_save(self):
        """Auto-populate details before saving"""
        if self.auto_populate and self.unlocode:
            self.populate_unlocode_details()
