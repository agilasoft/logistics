# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CostSheet(Document):
	def before_save(self):
		"""Update total_rates from charges table."""
		charges = self.get("charges") or []
		self.total_rates = len(charges)
