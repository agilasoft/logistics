# -*- coding: utf-8 -*-
# Copyright (c) 2020, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _


class TransportOrderPackage(Document):
	def before_insert(self):
		"""Set default dimension/volume/weight UOM from Logistics Settings when creating a new package row."""
		self._apply_default_uoms()

	def validate(self):
		"""Calculate volume from dimensions (Dimension Volume UOM Conversion) and validate temperature. Chargeable weight is computed on parent Transport Order."""
		self.calculate_volume()
		self.validate_temperature()

	def _apply_default_uoms(self):
		"""Apply default dimension_uom, volume_uom and weight_uom from Logistics Settings if not set."""
		from logistics.utils.measurements import get_default_uoms
		company = self._get_parent_company()
		defaults = get_default_uoms(company=company)
		if not getattr(self, "dimension_uom", None) and defaults.get("dimension"):
			self.dimension_uom = defaults["dimension"]
		if not getattr(self, "volume_uom", None) and defaults.get("volume"):
			self.volume_uom = defaults["volume"]
		if not getattr(self, "weight_uom", None) and defaults.get("weight"):
			self.weight_uom = defaults["weight"]

	def _get_parent_company(self):
		"""Get company from parent Transport Order."""
		if self.get("parenttype") == "Transport Order" and self.get("parent"):
			# Skip if parent name is still temporary (starts with "new-")
			# This can happen during document creation before the parent is fully saved
			if self.parent and self.parent.startswith("new-"):
				return None
			# Check if parent exists before trying to get value
			if not frappe.db.exists("Transport Order", self.parent):
				return None
			return frappe.db.get_value("Transport Order", self.parent, "company")
		return None

	def calculate_volume(self):
		"""Calculate volume from length, width, height using Dimension Volume UOM Conversion."""
		if not self.length or not self.width or not self.height:
			if getattr(self, "volume", None) is None:
				self.volume = 0
			return
		from logistics.utils.measurements import (
			calculate_volume_from_dimensions,
			get_default_uoms,
		)
		dimension_uom = getattr(self, "dimension_uom", None)
		volume_uom = getattr(self, "volume_uom", None)
		company = self._get_parent_company()
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
