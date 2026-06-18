# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from frappe.model.document import Document
from frappe.utils import flt, get_datetime, time_diff_in_hours


class ITTicket(Document):
	def validate(self):
		if self.opened_on and self.closed_on:
			delta = time_diff_in_hours(get_datetime(self.closed_on), get_datetime(self.opened_on))
			self.tat_hours = max(flt(delta), 0.0)
		else:
			self.tat_hours = 0.0
