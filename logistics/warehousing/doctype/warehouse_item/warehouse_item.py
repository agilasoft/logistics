# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt


class WarehouseItem(Document):
	def validate(self):
		self.validate_volume_calculation()
		self.validate_tracking_exclusivity()
	
	def validate_volume_calculation(self):
		"""Validate that volume matches calculated volume from dimensions"""
		if self.length and self.width and self.height:
			calculated_volume = flt(self.length) * flt(self.width) * flt(self.height)
			
			# If volume is provided, check if it matches calculated volume
			if self.volume and abs(flt(self.volume) - calculated_volume) > 0.001:
				frappe.msgprint(
					_("Volume ({0}) does not match calculated volume ({1}) from dimensions. Please verify your entries.").format(
						self.volume, calculated_volume
					),
					title=_("Volume Mismatch"),
					indicator="orange"
				)
			elif not self.volume:
				# Auto-calculate volume if not provided
				self.volume = calculated_volume
	
	def validate_tracking_exclusivity(self):
		"""Validate that batch tracking and serial tracking cannot both be enabled"""
		if self.batch_tracking and self.serial_tracking:
			frappe.throw(
				_("Batch Tracking and Serial Tracking cannot both be enabled. Please enable only one tracking method."),
				title=_("Invalid Tracking Configuration")
			)
