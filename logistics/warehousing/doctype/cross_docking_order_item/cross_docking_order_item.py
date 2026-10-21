# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt


class CrossDockingOrderItem(Document):
	def validate(self):
		self.validate_volume_calculation()

	def validate_volume_calculation(self):
		"""Validate and auto-calculate volume from dimensions with UOM conversion."""
		if self.length and self.width and self.height:
			from logistics.warehousing.utils.volume_conversion import calculate_volume_from_dimensions

			dimension_uom = getattr(self, "dimension_uom", None)
			volume_uom = getattr(self, "volume_uom", None)

			company = None
			if not dimension_uom or not volume_uom:
				if self.parent and frappe.db.exists("Cross-Docking Order", self.parent):
					company = frappe.db.get_value("Cross-Docking Order", self.parent, "company")
				if not company:
					company = frappe.defaults.get_user_default("Company")
				from logistics.utils.default_uom import measurement_default_uom
				if not dimension_uom:
					dimension_uom = measurement_default_uom("dimension", company=company)
				if not volume_uom:
					volume_uom = measurement_default_uom("volume", company=company)

			calculated_volume = calculate_volume_from_dimensions(
				length=self.length,
				width=self.width,
				height=self.height,
				dimension_uom=dimension_uom,
				volume_uom=volume_uom,
				company=company
			)

			if self.volume and abs(flt(self.volume) - calculated_volume) > 0.001:
				frappe.msgprint(
					_("Volume ({0}) does not match calculated volume ({1}) from dimensions. Please verify your entries.").format(
						self.volume, calculated_volume
					),
					title=_("Volume Mismatch"),
					indicator="orange"
				)
			elif not self.volume:
				self.volume = calculated_volume
