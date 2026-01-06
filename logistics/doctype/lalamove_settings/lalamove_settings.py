# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class LalamoveSettings(Document):
    def validate(self):
        """Validate Lalamove Settings"""
        if self.enabled:
            if not self.api_key:
                frappe.throw("API Key is required when integration is enabled")
            if not self.api_secret:
                frappe.throw("API Secret is required when integration is enabled")
            if not self.market:
                frappe.throw("Market Code is required when integration is enabled")


