# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class ContainerCharge(Document):
	def validate(self):
		if flt(self.quantity) and flt(self.unit_rate):
			self.total_amount = flt(self.quantity) * flt(self.unit_rate)
