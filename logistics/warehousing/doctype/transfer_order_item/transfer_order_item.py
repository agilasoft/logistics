# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt


class TransferOrderItem(Document):
	def validate(self):
		self.validate_volume_calculation()
	
	def validate_volume_calculation(self):
		"""Validate and auto-calculate volume from dimensions with UOM conversion"""
		if self.length and self.width and self.height:
			from logistics.warehousing.utils.volume_conversion import calculate_volume_from_dimensions
			
			# Get UOMs from item or warehouse settings
			dimension_uom = getattr(self, 'dimension_uom', None)
			volume_uom = getattr(self, 'volume_uom', None)
			
			# Get defaults from warehouse settings if not in item
			company = None
			if not dimension_uom or not volume_uom:
				try:
					# Try to get company from parent Transfer Order
					if self.parent:
						parent_doc = frappe.get_cached_doc("Transfer Order", self.parent)
						company = getattr(parent_doc, 'company', None)
					
					# Fallback to user default company
					if not company:
						company = frappe.defaults.get_user_default("Company")
					
					if company:
						warehouse_settings = frappe.get_cached_doc("Warehouse Settings", company)
						if not dimension_uom:
							dimension_uom = warehouse_settings.default_dimension_uom
						if not volume_uom:
							volume_uom = warehouse_settings.default_volume_uom
				except Exception:
					pass
			
			calculated_volume = calculate_volume_from_dimensions(
				length=self.length,
				width=self.width,
				height=self.height,
				dimension_uom=dimension_uom,
				volume_uom=volume_uom,
				company=company
			)
			
			# If volume is provided, check if it matches calculated volume (with tolerance for UOM conversion)
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
