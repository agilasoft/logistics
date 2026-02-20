# Copyright (c) 2025, logistics.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class AirBookingPackages(Document):
	def before_insert(self):
		"""Set default dimension/volume/weight UOM from settings when creating a new package row."""
		self._apply_default_uoms()

	def validate(self):
		"""Calculate volume from dimensions and chargeable weight using parent Air Booking divisor settings."""
		self.calculate_volume()
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
		"""Get company from parent Air Booking."""
		if self.get("parenttype") == "Air Booking" and self.get("parent"):
			return frappe.db.get_value("Air Booking", self.parent, "company")
		return None

	def calculate_volume(self):
		"""Calculate volume from length, width, height using Dimension Volume UOM Conversion. No fallback; conversion required."""
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

	def _get_parent_divisor(self):
		"""Get volume to weight divisor from parent Air Booking."""
		if self.get("parenttype") != "Air Booking" or not self.get("parent"):
			return 6000  # Default IATA standard
		
		try:
			parent = frappe.get_doc("Air Booking", self.parent)
			factor_type = getattr(parent, "volume_to_weight_factor_type", None) or "IATA"
			
			if factor_type == "IATA":
				return 6000
			elif factor_type == "Custom":
				# Check if custom divisor is overridden on Air Booking
				if getattr(parent, "custom_volume_to_weight_divisor", None):
					return flt(parent.custom_volume_to_weight_divisor)
				# Otherwise, get from Airline
				elif getattr(parent, "airline", None):
					airline_divisor = frappe.db.get_value("Airline", parent.airline, "volume_to_weight_divisor")
					if airline_divisor:
						return flt(airline_divisor)
			
			# Default to IATA if no custom settings
			return 6000
		except Exception:
			# If parent doesn't exist or error, default to IATA
			return 6000

	def calculate_chargeable_weight(self):
		"""Calculate chargeable weight based on package volume and weight using parent Air Booking divisor settings."""
		if not getattr(self, "volume", None) and not getattr(self, "weight", None):
			if hasattr(self, "chargeable_weight"):
				self.chargeable_weight = 0
			return
		
		# Get divisor from parent Air Booking
		divisor = self._get_parent_divisor()
		
		# Get package volume and weight (need to convert volume to m³ for calculation)
		package_volume = flt(getattr(self, "volume", 0) or 0)
		package_weight = flt(getattr(self, "weight", 0) or 0)
		
		# Convert volume to m³ if needed (assuming volume_uom conversion)
		# For chargeable weight calculation, we need volume in m³
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
		
		# Set chargeable_weight_uom to match weight_uom (typically "Kg")
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
