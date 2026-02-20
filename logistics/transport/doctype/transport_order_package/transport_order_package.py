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
		"""Calculate volume from dimensions (Dimension Volume UOM Conversion) and validate temperature."""
		self.calculate_volume()
		self.validate_temperature()
		self.calculate_chargeable_weight()

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

	def _get_volume_to_weight_divisor(self):
		"""Get volume to weight divisor from Transport Settings."""
		from frappe import flt
		try:
			settings = frappe.get_single("Transport Settings")
			divisor = getattr(settings, "volume_to_weight_divisor", None)
			if divisor:
				return flt(divisor)
		except Exception:
			pass
		# Default to 3000 (common road transport standard = 333 kg/m³)
		return 3000.0

	def calculate_chargeable_weight(self):
		"""Calculate chargeable weight based on package volume and weight using Transport Settings divisor."""
		from frappe import flt
		
		if not getattr(self, "volume", None) and not getattr(self, "weight", None):
			if hasattr(self, "chargeable_weight"):
				self.chargeable_weight = 0
			return
		
		# Get divisor from Transport Settings
		divisor = self._get_volume_to_weight_divisor()
		
		# Get package volume and weight
		package_volume = flt(getattr(self, "volume", 0) or 0)
		package_weight = flt(getattr(self, "weight", 0) or 0)
		
		# Convert volume to m³ if needed
		volume_in_m3 = package_volume
		if package_volume > 0:
			from logistics.utils.measurements import convert_volume, get_default_uoms
			volume_uom = getattr(self, "volume_uom", None)
			company = self._get_parent_company()
			defaults = get_default_uoms(company=company)
			target_volume_uom = defaults.get("volume")  # Typically "M³"
			
			if volume_uom and target_volume_uom and str(volume_uom).strip().upper() != str(target_volume_uom).strip().upper():
				try:
					volume_in_m3 = convert_volume(
						package_volume,
						from_uom=volume_uom,
						to_uom=target_volume_uom,
						company=company,
					)
				except Exception:
					volume_in_m3 = package_volume
		
		# Calculate volume weight
		volume_weight = 0
		if volume_in_m3 > 0 and divisor:
			# Convert volume from m³ to cm³, then divide by divisor
			# Volume in m³ * 1,000,000 cm³/m³ / divisor = volume weight in kg
			volume_weight = volume_in_m3 * (1000000.0 / divisor)
		
		# Calculate chargeable weight (higher of actual weight or volume weight)
		if package_weight > 0 and volume_weight > 0:
			self.chargeable_weight = max(package_weight, volume_weight)
		elif package_weight > 0:
			self.chargeable_weight = package_weight
		elif volume_weight > 0:
			self.chargeable_weight = volume_weight
		else:
			self.chargeable_weight = 0
		
		# Set chargeable_weight_uom to match weight_uom if not set
		if not getattr(self, "chargeable_weight_uom", None):
			weight_uom = getattr(self, "weight_uom", None)
			if weight_uom:
				self.chargeable_weight_uom = weight_uom
			else:
				from logistics.utils.measurements import get_default_uoms
				company = self._get_parent_company()
				defaults = get_default_uoms(company=company)
				if defaults.get("weight"):
					self.chargeable_weight_uom = defaults["weight"]
