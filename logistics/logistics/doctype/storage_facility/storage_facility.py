# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.contacts.address_and_contact import load_address_and_contact


class StorageFacility(Document):
	def onload(self):
		load_address_and_contact(self)
