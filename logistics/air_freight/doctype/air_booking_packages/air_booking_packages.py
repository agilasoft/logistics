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
		company = self._get_parent_company()
		defaults = self._get_safe_default_uoms(company=company)
		if not getattr(self, "dimension_uom", None) and defaults.get("dimension"):
			self.dimension_uom = defaults["dimension"]
		if not getattr(self, "volume_uom", None) and defaults.get("volume"):
			self.volume_uom = defaults["volume"]
		if not getattr(self, "weight_uom", None) and defaults.get("weight"):
			self.weight_uom = defaults["weight"]
	
	def _get_safe_default_uoms(self, company=None):
		"""Get default UOMs with fallbacks - never throws, always returns a dict."""
		from logistics.utils.measurements import get_default_uoms
		try:
			return get_default_uoms(company=company)
		except Exception as e:
			# If Logistics Settings are not configured, return empty dict
			# Callers should handle missing UOMs gracefully
			frappe.log_error(
				f"Could not get default UOMs (company={company}): {str(e)}. "
				"Please configure Logistics Settings with default UOMs.",
				"Air Booking Package - Default UOM Warning"
			)
			return {"dimension": None, "volume": None, "weight": None, "chargeable_weight": None}

	def _get_parent_company(self):
		"""Get company from parent Air Booking. Works with both saved and unsaved parents."""
		if self.get("parenttype") == "Air Booking" and self.get("parent"):
			# Skip if parent name is still temporary (starts with "new-")
			# This can happen during document creation before the parent is fully saved
			if self.parent and self.parent.startswith("new-"):
				# Fallback to user default company
				try:
					return frappe.defaults.get_user_default("Company")
				except Exception:
					return None
			# Check if parent exists before trying to get value
			if frappe.db.exists("Air Booking", self.parent):
				try:
					company = frappe.db.get_value("Air Booking", self.parent, "company")
					if company:
						return company
				except Exception:
					pass
		# Fallback: try to get company from user defaults
		try:
			return frappe.defaults.get_user_default("Company")
		except Exception:
			return None

	def calculate_volume(self):
		"""Calculate volume from length, width, height using Dimension Volume UOM Conversion. 
		Includes robust fallbacks: always computes volume when dimensions are provided."""
		if not self.length or not self.width or not self.height:
			if getattr(self, "volume", None) is None:
				self.volume = 0
			return
		
		# Validate dimensions are non-negative
		length = flt(self.length)
		width = flt(self.width)
		height = flt(self.height)
		
		if length < 0 or width < 0 or height < 0:
			frappe.log_error(
				f"Negative dimensions for Air Booking Package {self.name}: "
				f"length={length}, width={width}, height={height}. Setting volume to 0.",
				"Air Booking Package - Negative Dimensions"
			)
			self.volume = 0
			return
		
		# Calculate raw volume first (always available)
		raw_volume = length * width * height
		
		from logistics.utils.measurements import (
			calculate_volume_from_dimensions,
			ConversionNotFoundError,
		)
		dimension_uom = getattr(self, "dimension_uom", None)
		volume_uom = getattr(self, "volume_uom", None)
		company = self._get_parent_company()
		
		# Try to get defaults safely (never throws)
		defaults = self._get_safe_default_uoms(company=company)
		dimension_uom = dimension_uom or defaults.get("dimension")
		volume_uom = volume_uom or defaults.get("volume")
		
		# If no UOMs at all, use raw volume as fallback
		if not dimension_uom or not volume_uom:
			frappe.log_error(
				f"Missing UOMs for Air Booking Package {self.name}: dimension_uom={dimension_uom}, volume_uom={volume_uom}. "
				f"Using raw volume ({raw_volume}) as fallback.",
				"Air Booking Package - Missing UOMs Fallback"
			)
			self.volume = raw_volume
			return
		
		# Try proper calculation with conversion
		# Ensure UOMs are not empty strings (convert to None if empty)
		dimension_uom = dimension_uom if dimension_uom and str(dimension_uom).strip() else None
		volume_uom = volume_uom if volume_uom and str(volume_uom).strip() else None
		
		# Double-check: if UOMs are still missing after normalization, use fallback
		if not dimension_uom or not volume_uom:
			frappe.log_error(
				f"Missing UOMs after normalization for Air Booking Package {self.name}: dimension_uom={dimension_uom}, volume_uom={volume_uom}. "
				f"Using raw volume ({raw_volume}) as fallback.",
				"Air Booking Package - Missing UOMs After Normalization"
			)
			self.volume = raw_volume
			return
		
		try:
			calculated_volume = calculate_volume_from_dimensions(
				length=length,
				width=width,
				height=height,
				dimension_uom=dimension_uom,
				volume_uom=volume_uom,
				company=company,
			)
			# Validate calculated volume is non-negative
			if calculated_volume < 0:
				frappe.log_error(
					f"Negative calculated volume ({calculated_volume}) for Air Booking Package {self.name}. Using raw volume as fallback.",
					"Air Booking Package - Negative Calculated Volume"
				)
				self.volume = raw_volume
			else:
				self.volume = calculated_volume
		except ConversionNotFoundError as e:
			# Conversion factor missing - use intelligent fallback
			frappe.log_error(
				f"Volume conversion factor missing for Air Booking Package {self.name}: {str(e)}. Using fallback calculation.",
				"Air Booking Package - Conversion Missing"
			)
			self.volume = self._calculate_volume_fallback(length, width, height, dimension_uom, volume_uom, raw_volume)
		except (frappe.ValidationError, frappe.exceptions.ValidationError) as e:
			# Handle frappe.throw() exceptions (ValidationError) - usually from get_default_uoms()
			frappe.log_error(
				f"Volume calculation validation error for Air Booking Package {self.name}: {str(e)}. Using fallback calculation.",
				"Air Booking Package - Volume Calculation Validation Error"
			)
			self.volume = self._calculate_volume_fallback(length, width, height, dimension_uom, volume_uom, raw_volume)
		except Exception as e:
			# Any other error - use fallback
			frappe.log_error(
				f"Volume calculation failed for Air Booking Package {self.name}: {str(e)}. Using fallback calculation.",
				"Air Booking Package - Volume Calculation Error"
			)
			self.volume = self._calculate_volume_fallback(length, width, height, dimension_uom, volume_uom, raw_volume)
	
	def _calculate_volume_fallback(self, length, width, height, dimension_uom, volume_uom, raw_volume):
		"""Fallback volume calculation when conversion factors are missing."""
		# If dimension and volume UOMs are the same (case-insensitive), use raw volume
		if dimension_uom and volume_uom and str(dimension_uom).strip().upper() == str(volume_uom).strip().upper():
			return raw_volume
		
		# Try common conversion heuristics
		dim_upper = str(dimension_uom or "").strip().upper()
		vol_upper = str(volume_uom or "").strip().upper()
		
		# Common conversions (heuristic fallbacks)
		# Centimeter to Cubic Meter: 1 cm³ = 0.000001 m³
		if ("CENTIMETER" in dim_upper or "CM" == dim_upper) and ("CUBIC METER" in vol_upper or "M³" in vol_upper or "M3" == vol_upper):
			return raw_volume * 0.000001
		# Meter to Cubic Meter: 1 m³ = 1 m³ (same)
		if ("METER" in dim_upper or "M" == dim_upper) and ("CUBIC METER" in vol_upper or "M³" in vol_upper or "M3" == vol_upper):
			return raw_volume
		# Inch to Cubic Foot: 1 in³ = 0.000578704 ft³
		if ("INCH" in dim_upper or "IN" == dim_upper) and ("CUBIC FOOT" in vol_upper or "FT³" in vol_upper or "CFT" == vol_upper):
			return raw_volume * 0.000578704
		# Foot to Cubic Foot: 1 ft³ = 1 ft³ (same)
		if ("FOOT" in dim_upper or "FT" == dim_upper) and ("CUBIC FOOT" in vol_upper or "FT³" in vol_upper or "CFT" == vol_upper):
			return raw_volume
		
		# Last resort: use raw volume (may be incorrect but better than 0)
		frappe.log_error(
			f"Using raw volume ({raw_volume}) as fallback. UOMs: dimension={dimension_uom}, volume={volume_uom}. "
			"This may be incorrect if UOMs differ. Please configure Dimension Volume UOM Conversion.",
			"Air Booking Package - Raw Volume Fallback"
		)
		return raw_volume

	def _get_parent_divisor(self):
		"""Get volume to weight divisor from parent Air Booking. Works with both saved and unsaved parents."""
		if self.get("parenttype") != "Air Booking" or not self.get("parent"):
			return 6000  # Default IATA standard
		
		# Skip if parent name is still temporary (starts with "new-")
		# This can happen during document creation before the parent is fully saved
		if self.parent and self.parent.startswith("new-"):
			return 6000  # Default IATA standard
		
		# Check if parent exists before trying to get value
		if not frappe.db.exists("Air Booking", self.parent):
			return 6000  # Default IATA standard for unsaved parents
		
		try:
			parent = frappe.get_doc("Air Booking", self.parent)
			factor_type = getattr(parent, "volume_to_weight_factor_type", None) or "IATA"
			
			if factor_type == "IATA":
				return 6000
			elif factor_type == "Custom":
				# Check if custom divisor is overridden on Air Booking
				if getattr(parent, "custom_volume_to_weight_divisor", None):
					divisor = flt(parent.custom_volume_to_weight_divisor)
					# Validate divisor is positive
					if divisor > 0:
						return divisor
					else:
						frappe.log_error(
							f"Invalid custom divisor ({divisor}) on Air Booking {self.parent}. Using default 6000.",
							"Air Booking Package - Invalid Custom Divisor"
						)
				# Otherwise, get from Airline
				elif getattr(parent, "airline", None):
					airline_divisor = frappe.db.get_value("Airline", parent.airline, "volume_to_weight_divisor")
					if airline_divisor:
						divisor = flt(airline_divisor)
						# Validate divisor is positive
						if divisor > 0:
							return divisor
						else:
							frappe.log_error(
								f"Invalid airline divisor ({divisor}) for Airline {parent.airline}. Using default 6000.",
								"Air Booking Package - Invalid Airline Divisor"
							)
			
			# Default to IATA if no custom settings
			return 6000
		except Exception as e:
			# If parent doesn't exist or error, default to IATA
			frappe.log_error(
				f"Error getting divisor from parent Air Booking {self.parent}: {str(e)}. Using default 6000.",
				"Air Booking Package - Divisor Retrieval Error"
			)
			return 6000

	def calculate_chargeable_weight(self):
		"""Calculate chargeable weight based on package volume and weight using parent Air Booking divisor settings."""
		if not getattr(self, "volume", None) and not getattr(self, "weight", None):
			if hasattr(self, "chargeable_weight"):
				self.chargeable_weight = 0
			return
		
		# Get divisor from parent Air Booking
		divisor = self._get_parent_divisor()
		
		# Validate divisor is positive
		if divisor <= 0:
			frappe.log_error(
				f"Invalid divisor ({divisor}) for Air Booking Package {self.name}. Using default 6000.",
				"Air Booking Package - Invalid Divisor"
			)
			divisor = 6000  # Default to IATA standard
		
		# Get package volume and weight (need to convert volume to m³ for calculation)
		package_volume = flt(getattr(self, "volume", 0) or 0)
		package_weight = flt(getattr(self, "weight", 0) or 0)
		
		# Validate non-negative values
		if package_volume < 0:
			frappe.log_error(
				f"Negative volume ({package_volume}) for Air Booking Package {self.name}. Setting to 0.",
				"Air Booking Package - Negative Volume"
			)
			package_volume = 0
		
		if package_weight < 0:
			frappe.log_error(
				f"Negative weight ({package_weight}) for Air Booking Package {self.name}. Setting to 0.",
				"Air Booking Package - Negative Weight"
			)
			package_weight = 0
		
		# Convert volume to m³ if needed (assuming volume_uom conversion)
		# For chargeable weight calculation, we need volume in m³
		volume_in_m3 = package_volume
		if package_volume > 0:
			from logistics.utils.measurements import convert_volume
			volume_uom = getattr(self, "volume_uom", None)
			company = self._get_parent_company()
			defaults = self._get_safe_default_uoms(company=company)
			target_volume_uom = defaults.get("volume")  # Typically "M³"
			
			if volume_uom and target_volume_uom and str(volume_uom).strip().upper() != str(target_volume_uom).strip().upper():
				try:
					volume_in_m3 = convert_volume(
						package_volume,
						from_uom=volume_uom,
						to_uom=target_volume_uom,
						company=company,
					)
					# Validate converted volume is non-negative
					if volume_in_m3 < 0:
						frappe.log_error(
							f"Negative converted volume ({volume_in_m3}) for Air Booking Package {self.name}. Using original volume.",
							"Air Booking Package - Negative Converted Volume"
						)
						volume_in_m3 = package_volume
				except Exception as e:
					# Log the error for debugging, but use original volume as fallback
					frappe.log_error(
						f"Volume conversion failed for Air Booking Package {self.name}: {str(e)}. "
						f"Volume UOM: {volume_uom}, Target UOM: {target_volume_uom}. "
						f"Using original volume value ({package_volume}) - assuming it's already in m³ for chargeable weight calculation.",
						"Air Booking Package - Volume Conversion Error"
					)
					# If conversion fails, assume volume is already in m³ (best-effort)
					volume_in_m3 = package_volume
			elif not target_volume_uom:
				# No target UOM available, assume volume is already in m³
				frappe.log_error(
					f"No target volume UOM available for Air Booking Package {self.name}. "
					f"Assuming volume ({package_volume}) is already in m³ for chargeable weight calculation.",
					"Air Booking Package - Missing Target Volume UOM"
				)
				volume_in_m3 = package_volume
		
		# Calculate volume weight
		volume_weight = 0
		if volume_in_m3 > 0 and divisor > 0:
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
				company = self._get_parent_company()
				defaults = self._get_safe_default_uoms(company=company)
				if defaults.get("weight"):
					self.chargeable_weight_uom = defaults["weight"]
