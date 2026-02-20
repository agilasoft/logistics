# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class TransportJobPackage(Document):
	def before_insert(self):
		"""Set default weight/volume UOM from Transport Settings when creating a new package row."""
		self._apply_default_uoms()

	def validate(self):
		"""Calculate volume from dimensions and validate temperature"""
		self.calculate_volume()
		self.validate_temperature()
	
	def validate_temperature(self):
		"""Validate temperature fields against global limits"""
		if not self.temp_controlled:
			return  # Skip validation if temperature control is not enabled
		
		# Use global temperature validation utility
		from logistics.utils.temperature_validation import validate_temperature_range
		
		# Validate temperature range against global limits and min < max
		if self.min_temperature is not None or self.max_temperature is not None:
			validate_temperature_range(
				min_temperature=self.min_temperature,
				max_temperature=self.max_temperature,
				min_field_label="Minimum Temperature",
				max_field_label="Maximum Temperature",
				raise_exception=True
			)

	def _apply_default_uoms(self):
		"""Apply default dimension_uom, weight_uom and volume_uom from Logistics Settings if not set."""
		from logistics.utils.measurements import get_default_uoms
		company = None
		if self.get("parenttype") == "Transport Job" and self.get("parent"):
			company = frappe.db.get_value("Transport Job", self.parent, "company")
		defaults = get_default_uoms(company=company)
		if not getattr(self, "dimension_uom", None) and defaults.get("dimension"):
			self.dimension_uom = defaults["dimension"]
		if not self.weight_uom and defaults.get("weight"):
			self.weight_uom = defaults["weight"]
		if not self.volume_uom and defaults.get("volume"):
			self.volume_uom = defaults["volume"]

	def calculate_volume(self):
		"""Calculate volume from length, width, height using Dimension Volume UOM Conversion. No fallback; conversion required."""
		if not self.length or not self.width or not self.height:
			self.volume = 0
			return
		from logistics.utils.measurements import (
			calculate_volume_from_dimensions,
			get_default_uoms,
		)
		dimension_uom = getattr(self, "dimension_uom", None)
		volume_uom = getattr(self, "volume_uom", None)
		company = None
		if self.get("parenttype") == "Transport Job" and self.get("parent"):
			company = frappe.db.get_value("Transport Job", self.parent, "company")
		if not dimension_uom or not volume_uom:
			defaults = get_default_uoms(company=company)
			dimension_uom = dimension_uom or defaults.get("dimension")
			volume_uom = volume_uom or defaults.get("volume")
		self.volume = calculate_volume_from_dimensions(
			length=self.length,
			width=self.width,
			height=self.height,
			dimension_uom=dimension_uom,
			volume_uom=volume_uom,
			company=company,
		)