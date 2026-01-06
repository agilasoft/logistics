# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class WarehouseJobItem(Document):
	def validate(self):
		"""Validate - volume and weight are handled by front-end only"""
		# Auto-calculate volume from dimensions if volume is not set
		if not self.volume or flt(self.volume) == 0:
			if self.length and self.width and self.height:
				calculated_volume = flt(self.length) * flt(self.width) * flt(self.height)
				if calculated_volume > 0:
					self.volume = calculated_volume
