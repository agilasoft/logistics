# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from frappe.model.document import Document
from frappe.utils import flt


class ITUptimeLog(Document):
	def validate(self):
		self.downtime_pct = max(0.0, 100.0 - flt(self.uptime_pct))
