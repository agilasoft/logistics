# -*- coding: utf-8 -*-
# Copyright (c) 2020, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class TransportBooking(Document):
	pass

	@frappe.whitelist()
	def create_job(self):
		doc = frappe.new_doc("Transport Job")
		doc.customer = self.customer
		doc.job_date = frappe.utils.nowdate()
		doc.transport_booking = self.name
		doc.customer_ref_no = self.customer_ref_no
		doc.hazardous = self.hazardous
		doc.refrigeration = self.refrigeration

		# Run through booking items and insert  job activities
		for items in self.vehicles:
			i = items.qty
			while i > 0:
				doc.append("activities", {
					"vehicle_type": items.vehicle_type,
					"pickup": items.origin,
					"delivery": items.destination 
				})
				i = i-1

		doc.packages = self.packages
		doc.internal_notes = self.internal_notes
		doc.client_notes = self.client_notes
		doc.flags.ignore_mandatory = True
		doc.insert()
