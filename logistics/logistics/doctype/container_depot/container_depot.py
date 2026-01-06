# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.contacts.doctype.address.address import get_address_display

class ContainerDepot(Document):
    def onload(self):
        # Populate frm.doc.__onload.addr_list / contact_list like Customer
        load_address_and_contact(self)

