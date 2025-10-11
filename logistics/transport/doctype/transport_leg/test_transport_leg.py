# Copyright (c) 2025, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.model.document import Document

class TestTransportLeg(FrappeTestCase):
	pass

# Optional: server-side safeguard to populate HTML on save
def _format_address_html(address_name: str) -> str:
    if not address_name:
        return ""
    # import ERPNext/Frappe address formatter
    from frappe.contacts.doctype.address.address import get_address_display
    try:
        # pass the Address name; function accepts name or dict
        return get_address_display(address_name) or ""
    except Exception:
        # fallback: fetch doc and pass dict (covers older signatures)
        ad = frappe.get_doc("Address", address_name).as_dict()
        return get_address_display(ad) or ""

class TransportLeg(Document):
    def validate(self):
        # Keep pick/drop HTML in sync server-side as well
        # (handles bulk operations, server inserts, etc.)
        if hasattr(self, "pick_address"):
            self.pick_address_html = _format_address_html(self.pick_address) \
                if hasattr(self, "pick_address_html") else getattr(self, "pick_address_format", None)
            if hasattr(self, "pick_address_format"):
                self.pick_address_format = _format_address_html(self.pick_address)

        if hasattr(self, "drop_address"):
            if hasattr(self, "drop_address_html"):
                self.drop_address_html = _format_address_html(self.drop_address)
