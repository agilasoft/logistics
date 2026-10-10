# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document


class IntercompanyInvoiceLog(Document):
	def validate(self):
		if not self.sales_quote and not self.get("periodic_billing"):
			frappe.throw(_("Sales Quote or Periodic Billing is required."))
