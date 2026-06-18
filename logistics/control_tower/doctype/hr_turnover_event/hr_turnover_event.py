# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from frappe.model.document import Document
from frappe.utils import date_diff, getdate


class HRTurnoverEvent(Document):
	def validate(self):
		if self.join_date and self.exit_date:
			months = max(0, int(date_diff(getdate(self.exit_date), getdate(self.join_date)) / 30))
			self.tenure_months = months
