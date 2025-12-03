# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class DimensionVolumeUOMConversion(Document):
	def validate(self):
		"""Validate the conversion factor and UOMs"""
		if self.conversion_factor <= 0:
			frappe.throw(_("Conversion Factor must be greater than 0"))
		
		# Check for duplicate combinations
		if self.is_new():
			existing = frappe.db.exists(
				"Dimension Volume UOM Conversion",
				{
					"dimension_uom": self.dimension_uom,
					"volume_uom": self.volume_uom,
					"name": ["!=", self.name]
				}
			)
			if existing:
				frappe.throw(
					_("A conversion from {0} to {1} already exists").format(
						self.dimension_uom, self.volume_uom
					)
				)

