# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class ChangeRequestCharge(Document):
	def validate(self):
		if self.quantity and self.unit_cost is not None:
			self.amount = frappe.utils.flt(self.quantity, precision=2) * frappe.utils.flt(
				self.unit_cost, precision=2
			)
