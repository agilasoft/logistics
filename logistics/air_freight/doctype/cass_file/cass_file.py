# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document

from logistics.air_freight.casslink.parser import guess_file_type


class CASSFile(Document):
	def before_insert(self):
		if not self.naming_series:
			self.naming_series = "CASF-.YYYY.-.#####"

	def validate(self):
		if self.settlement_period and not self.company:
			self.company = frappe.db.get_value(
				"CASS Settlement Period", self.settlement_period, "company"
			)
		if self.attached_file:
			filename = (self.attached_file or "").rsplit("/", 1)[-1]
			self.file_type = guess_file_type(filename)
		if not self.direction:
			self.direction = "Inbound"
		if not self.status:
			self.status = "Draft"

	@frappe.whitelist()
	def process_file(self):
		self.check_permission("write")
		from logistics.air_freight.casslink.service import process_cass_file

		return process_cass_file(self)
