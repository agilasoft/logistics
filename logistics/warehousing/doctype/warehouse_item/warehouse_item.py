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
			from logistics.warehousing.utils.volume_conversion import calculate_volume_from_dimensions
			
			# Get UOMs from item or warehouse settings
			dimension_uom = getattr(self, 'dimension_uom', None)
			volume_uom = getattr(self, 'volume_uom', None)
			
			# Get defaults from warehouse settings if not in item
			# Try to get company from customer if available
			company = None
			if not dimension_uom or not volume_uom:
				try:
					if self.customer:
						# Try to get company from customer's default company
						customer_doc = frappe.get_cached_doc("Customer", self.customer)
						company = customer_doc.default_company
					
					if company:
						warehouse_settings = frappe.get_cached_doc("Warehouse Settings", company)
						if not dimension_uom:
							dimension_uom = warehouse_settings.default_dimension_uom
						if not volume_uom:
							volume_uom = warehouse_settings.default_volume_uom
				except:
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
	
	def validate_tracking_exclusivity(self):
		"""Validate that batch tracking and serial tracking cannot both be enabled"""
		if self.batch_tracking and self.serial_tracking:
			frappe.throw(
				_("Batch Tracking and Serial Tracking cannot both be enabled. Please enable only one tracking method."),
				title=_("Invalid Tracking Configuration")
			)
