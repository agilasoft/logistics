# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe import _
from frappe.utils import now


class CapacityReservation(Document):
	def validate(self):
		"""Validate capacity reservation"""
		if not self.vehicle:
			frappe.throw(_("Vehicle is required"))
		
		if not self.reservation_date:
			frappe.throw(_("Reservation date is required"))
		
		# Set reserved_by if not set
		if not self.reserved_by:
			self.reserved_by = frappe.session.user
	
	def before_insert(self):
		"""Set default status"""
		if not self.status:
			self.status = "Reserved"
	
	def on_update(self):
		"""Handle status changes"""
		if self.status == "Released" and not self.released_at:
			self.released_at = now()
