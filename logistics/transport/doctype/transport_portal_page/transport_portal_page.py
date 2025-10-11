# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class TransportPortalPage(Document):
    def validate(self):
        """Validate transport portal page configuration"""
        if not self.route:
            self.route = "/transport-portal"
            
        # Ensure route starts with /
        if not self.route.startswith('/'):
            self.route = '/' + self.route
    
    def get_portal_config(self):
        """Get portal configuration"""
        return {
            "title": self.title,
            "route": self.route,
            "is_active": self.is_active,
            "content_type": self.content_type,
            "template_path": self.template_path,
            "show_vehicle_tracking": self.show_vehicle_tracking,
            "show_route_map": self.show_route_map,
            "show_job_details": self.show_job_details,
            "show_leg_details": self.show_leg_details
        }

