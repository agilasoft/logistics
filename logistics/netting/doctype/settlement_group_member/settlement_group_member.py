# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class SettlementGroupMember(Document):
	def validate(self):
		"""Validate settlement group member."""
		self.fetch_party_name()
	
	def fetch_party_name(self):
		"""Fetch party name from Customer or Supplier."""
		if not self.party or not self.party_type:
			return
		
		try:
			if self.party_type == "Customer":
				party_name = frappe.db.get_value("Customer", self.party, "customer_name")
				if party_name:
					self.party_name = party_name
			elif self.party_type == "Supplier":
				party_name = frappe.db.get_value("Supplier", self.party, "supplier_name")
				if party_name:
					self.party_name = party_name
		except Exception:
			# If party doesn't exist or error occurs, leave party_name as is
			pass


