# Copyright (c) 2025, logistics.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class SeaBookingPackages(Document):
	def before_insert(self):
		"""Set default dimension/volume/weight UOM from settings when creating a new package row."""
		self._apply_default_uoms()

	def validate(self):
		"""Calculate volume from dimensions (Dimension Volume UOM Conversion) and calculate chargeable weight."""
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
		"""Get company from parent Sea Booking."""
		if self.get("parenttype") == "Sea Booking" and self.get("parent"):
			# Skip if parent name is still temporary (starts with "new-")
			# This can happen during document creation before the parent is fully saved
			if self.parent and self.parent.startswith("new-"):
				return None
			# Check if parent exists before trying to get value
			if not frappe.db.exists("Sea Booking", self.parent):
				return None
			return frappe.db.get_value("Sea Booking", self.parent, "company")
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

	def _get_volume_to_weight_divisor(self):
		"""Get volume to weight divisor from Sea Freight Settings.
		Converts volume_to_weight_factor (kg/m³) to divisor format.
		Formula: divisor = 1,000,000 / factor
		Example: factor = 1000 kg/m³ → divisor = 1000
		"""
		from frappe import flt
		try:
			settings = frappe.get_single("Sea Freight Settings")
			factor = getattr(settings, "volume_to_weight_factor", None)
			if factor:
				# Convert factor (kg/m³) to divisor: divisor = 1,000,000 / factor
				# This matches the transport_order formula: volume_weight = volume (m³) * 1,000,000 / divisor
				return flt(1000000.0 / flt(factor))
		except Exception:
			pass
		# Default to 1000 (equivalent to 1000 kg/m³ factor, common sea freight standard)
		return 1000.0
	
	def _get_chargeable_weight_calculation_method(self):
		"""Get the chargeable weight calculation method from Sea Freight Settings.
		Returns: 'Actual Weight', 'Volume Weight', or 'Higher of Both' (default)
		"""
		try:
			settings = frappe.get_single("Sea Freight Settings")
			method = getattr(settings, "chargeable_weight_calculation", None)
			if method in ["Actual Weight", "Volume Weight", "Higher of Both"]:
				return method
		except Exception:
			pass
		# Default to "Higher of Both" (common sea freight standard)
		return "Higher of Both"

	def calculate_chargeable_weight(self):
		"""Calculate chargeable weight based on package volume and weight using Sea Freight Settings divisor.
		Respects chargeable_weight_calculation setting: 'Actual Weight', 'Volume Weight', or 'Higher of Both'.
		"""
		from frappe import flt
		
		# Get package volume and weight first
		package_volume = flt(getattr(self, "volume", 0) or 0)
		package_weight = flt(getattr(self, "weight", 0) or 0)
		
		# If both volume and weight are zero or missing, set chargeable weight to 0
		if not package_volume and not package_weight:
			if hasattr(self, "chargeable_weight"):
				self.chargeable_weight = 0
			return
		
		# Get divisor and calculation method from Sea Freight Settings
		divisor = self._get_volume_to_weight_divisor()
		calculation_method = self._get_chargeable_weight_calculation_method()
		
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
					converted_volume = convert_volume(
						package_volume,
						from_uom=volume_uom,
						to_uom=target_volume_uom,
						company=company,
					)
					# Only use converted volume if it's valid and positive
					if converted_volume and converted_volume > 0:
						volume_in_m3 = converted_volume
					# Otherwise fall back to original volume
				except Exception:
					# Fall back to original volume if conversion fails
					pass
		
		# Convert weight to base weight unit (kg) if needed
		# Volume weight is calculated in kg, so package weight must also be in kg for correct comparison
		package_weight_in_kg = package_weight
		if package_weight > 0:
			from logistics.utils.measurements import convert_weight, get_default_uoms
			weight_uom = getattr(self, "weight_uom", None)
			company = self._get_parent_company()
			defaults = get_default_uoms(company=company)
			target_weight_uom = defaults.get("weight")  # Typically "Kg"
			
			if weight_uom and target_weight_uom and str(weight_uom).strip().upper() != str(target_weight_uom).strip().upper():
				try:
					converted_weight = convert_weight(
						package_weight,
						from_uom=weight_uom,
						to_uom=target_weight_uom,
						company=company,
					)
					# Only use converted weight if it's valid and positive
					if converted_weight and converted_weight > 0:
						package_weight_in_kg = converted_weight
					# Otherwise fall back to original weight
				except Exception:
					# Fall back to original weight if conversion fails
					pass
		
		# Calculate volume weight (result is in kg)
		volume_weight = 0
		if volume_in_m3 > 0 and divisor and divisor > 0:
			# Convert volume from m³ to cm³, then divide by divisor
			# Volume in m³ * 1,000,000 cm³/m³ / divisor = volume weight in kg
			volume_weight = volume_in_m3 * (1000000.0 / divisor)
		
		# Calculate chargeable weight based on calculation method
		if calculation_method == "Actual Weight":
			# Use only actual weight
			chargeable = package_weight_in_kg
		elif calculation_method == "Volume Weight":
			# Use only volume weight
			chargeable = volume_weight
		else:  # "Higher of Both" (default)
			# Use the higher of actual weight or volume weight
			if package_weight_in_kg > 0 and volume_weight > 0:
				chargeable = max(package_weight_in_kg, volume_weight)
			elif package_weight_in_kg > 0:
				chargeable = package_weight_in_kg
			elif volume_weight > 0:
				chargeable = volume_weight
			else:
				chargeable = 0
		
		# Always set chargeable_weight, even if it's 0
		self.chargeable_weight = chargeable
		
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
