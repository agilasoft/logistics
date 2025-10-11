# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class IATASettings(Document):
    def validate(self):
        """Validate IATA Settings"""
        if self.cargo_xml_enabled and not self.cargo_xml_endpoint:
            frappe.throw("Cargo-XML Endpoint URL is required when Cargo-XML is enabled")
        
        if self.cargo_xml_enabled and not self.cargo_xml_username:
            frappe.throw("Username is required when Cargo-XML is enabled")
        
        if self.cargo_xml_enabled and not self.cargo_xml_password:
            frappe.throw("Password is required when Cargo-XML is enabled")
        
        if self.dg_autocheck_enabled and not self.dg_autocheck_api_key:
            frappe.throw("DG AutoCheck API Key is required when DG AutoCheck is enabled")
        
        if self.cass_enabled and not self.cass_participant_code:
            frappe.throw("CASS Participant Code is required when CASSLink is enabled")
        
        if self.cass_enabled and not self.cass_api_endpoint:
            frappe.throw("CASS API Endpoint is required when CASSLink is enabled")
        
        if self.tact_subscription and not self.tact_api_key:
            frappe.throw("TACT API Key is required when TACT Subscription is enabled")
        
        if self.tact_subscription and not self.tact_endpoint:
            frappe.throw("TACT Endpoint is required when TACT Subscription is enabled")

    def on_update(self):
        """Called after saving"""
        frappe.msgprint("IATA Settings updated successfully")
        
        # Clear cache to ensure changes take effect
        frappe.clear_cache()
        
        # Log the update
        frappe.logger().info(f"IATA Settings updated by {frappe.session.user}")