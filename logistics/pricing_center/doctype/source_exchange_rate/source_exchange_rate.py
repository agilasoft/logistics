# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
class SourceExchangeRate(Document):
	def validate(self):
		if not (self.exchange_rate_source and self.currency and self.date):
			return
		existing = frappe.db.get_value(
			"Source Exchange Rate",
			{
				"exchange_rate_source": self.exchange_rate_source,
				"currency": self.currency,
				"date": self.date,
			},
			"name",
		)
		if existing and existing != self.name:
			frappe.throw(
				_("An exchange rate already exists for this Source, Currency and Date."),
				title=_("Duplicate"),
			)
