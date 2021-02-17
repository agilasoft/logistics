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
		doc.instructions = self.instructions
		doc.packages = self.packages
		doc.internal_notes = self.internal_notes
		doc.client_notes = self.client_notes
		doc.flags.ignore_mandatory = True
		doc.insert()
