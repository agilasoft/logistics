# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from frappe.model.document import Document
from frappe.utils import flt


class HRLaborCostPeriod(Document):
	def validate(self):
		self.variance_amount = flt(self.actual_amount) - flt(self.budget_amount)
