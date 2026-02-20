# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SeaBookingRoutingLeg(Document):
	def before_insert(self):
		if not self.leg_order and self.get("parent"):
			max_order = frappe.db.sql(
				"""
				SELECT COALESCE(MAX(leg_order), 0) FROM `tabSea Booking Routing Leg`
				WHERE parent = %s AND parenttype = 'Sea Booking'
				""",
				self.parent,
			)
			self.leg_order = (max_order[0][0] + 1) if max_order else 1
