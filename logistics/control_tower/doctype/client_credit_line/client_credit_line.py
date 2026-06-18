# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from frappe.model.document import Document
from frappe.utils import flt


class ClientCreditLine(Document):
	def validate(self):
		self.available_amount = max(0.0, flt(self.credit_limit) - flt(self.exposure_amount))
