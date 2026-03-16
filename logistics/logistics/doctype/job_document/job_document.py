# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, date_diff, today


class JobDocument(Document):
	"""Child table for document tracking on Bookings, Jobs, Shipments."""

	def before_save(self):
		if not self.get("source"):
			self.source = "Manual"
		if not self.get("created_at"):
			self.created_at = frappe.utils.now()
		self.apply_activity_based_status_updates()
		self.update_overdue_status()

	def apply_activity_based_status_updates(self):
		"""Set date_received/Received on attachment; date_verified/Verified on is_verified."""
		today_date = getdate(today())
		# Attachment set -> Received (if still Pending/Uploaded)
		if self.get("attachment") and self.status in ("Pending", "Uploaded"):
			self.date_received = today_date
			self.status = "Received"
		# Verified -> Verified (if not already Verified/Done)
		if self.get("is_verified") and self.status not in ("Verified", "Done"):
			self.date_verified = today_date
			self.status = "Verified"

	def update_overdue_status(self):
		"""Update overdue_days and status when date_required or expiry_date has passed."""
		today_date = getdate(today())

		# Expired: expiry_date passed
		if self.expiry_date and getdate(self.expiry_date) < today_date:
			self.status = "Expired"
			return

		# Overdue: date_required passed, required document not received
		if self.date_required:
			required = getdate(self.date_required)
			if required < today_date and self.status in ("Pending", "Uploaded"):
				self.overdue_days = date_diff(today_date, required)
				if self.status == "Pending":
					self.status = "Overdue"
			elif self.overdue_days:
				self.overdue_days = 0
