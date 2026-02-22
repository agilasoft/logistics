# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, date_diff, today


class JobDocument(Document):
	"""Child table for document tracking on Bookings, Jobs, Shipments."""

	def before_save(self):
		self.update_overdue_status()

	def update_overdue_status(self):
		"""Update overdue_days and status when date_required has passed."""
		if not self.date_required:
			return
		required = getdate(self.date_required)
		today_date = getdate(today())
		if required < today_date and self.status in ("Pending", "Uploaded"):
			self.overdue_days = date_diff(today_date, required)
			if self.status == "Pending":
				self.status = "Overdue"
		elif self.overdue_days:
			self.overdue_days = 0
