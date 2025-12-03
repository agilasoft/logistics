# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Volume Conversion Utility Module

This module provides functions to convert volume calculations from dimension UOMs
to volume UOMs, handling cases where dimensions are in one unit (e.g., centimeters)
and volume needs to be in another unit (e.g., cubic meters).
"""

import frappe
from frappe import _
from frappe.utils import flt
from typing import Optional, Dict


class ConversionNotFoundError(Exception):
	"""Raised when a conversion factor cannot be found"""
	pass


# Standard conversion factors for common UOM combinations
STANDARD_CONVERSIONS = {
	# Centimeter to Cubic Meter
	("CM", "CBM"): 0.000001,  # 1 cm³ = 0.000001 m³
	("cm", "CBM"): 0.000001,
	("cm", "cbm"): 0.000001,
	("CM", "cbm"): 0.000001,
	
	# Meter to Cubic Meter
	("M", "CBM"): 1.0,  # 1 m³ = 1 m³
	("m", "CBM"): 1.0,
	("M", "cbm"): 1.0,
	("m", "cbm"): 1.0,
	
	# Millimeter to Cubic Meter
	("MM", "CBM"): 0.000000001,  # 1 mm³ = 0.000000001 m³
	("mm", "CBM"): 0.000000001,
	("MM", "cbm"): 0.000000001,
	("mm", "cbm"): 0.000000001,
	
	# Inch to Cubic Feet
	("IN", "CFT"): 0.000578704,  # 1 in³ = 1/1728 ft³ ≈ 0.000578704 ft³
	("in", "CFT"): 0.000578704,
	("IN", "cft"): 0.000578704,
	("in", "cft"): 0.000578704,
	
	# Feet to Cubic Feet
	("FT", "CFT"): 1.0,  # 1 ft³ = 1 ft³
	("ft", "CFT"): 1.0,
	("FT", "cft"): 1.0,
	("ft", "cft"): 1.0,
	
	# Centimeter to Cubic Centimeter (no conversion needed, but for consistency)
	("CM", "CM3"): 1.0,
	("cm", "CM3"): 1.0,
	("CM", "cm3"): 1.0,
	("cm", "cm3"): 1.0,
}


def get_volume_conversion_factor(
	dimension_uom: str,
	volume_uom: str,
	company: Optional[str] = None
) -> float:
	"""
	Get conversion factor from dimension UOM to volume UOM.
	
	First checks custom conversions in the database, then falls back to
	standard conversions.
	
	Args:
		dimension_uom: UOM of dimensions (e.g., "CM", "M")
		volume_uom: UOM of volume (e.g., "CBM", "CFT")
		company: Optional company for company-specific conversions
	
	Returns:
		Conversion factor (float)
	
	Raises:
		ConversionNotFoundError: If conversion not found and no fallback available
	"""
	if not dimension_uom or not volume_uom:
		raise ConversionNotFoundError(
			_("Dimension UOM and Volume UOM are required")
		)
	
	# Normalize UOMs (uppercase)
	dim_uom = dimension_uom.upper().strip()
	vol_uom = volume_uom.upper().strip()
	
	# Check if they're the same (no conversion needed)
	if dim_uom == vol_uom:
		return 1.0
	
	# Try to get custom conversion from database
	try:
		conversion = frappe.db.get_value(
			"Dimension Volume UOM Conversion",
			{
				"dimension_uom": dimension_uom,
				"volume_uom": volume_uom,
				"enabled": 1
			},
			"conversion_factor",
			as_dict=True
		)
		
		if conversion and conversion.get("conversion_factor"):
			return flt(conversion.get("conversion_factor"))
	except Exception:
		pass  # Fall through to standard conversions
	
	# Try standard conversions
	key = (dim_uom, vol_uom)
	if key in STANDARD_CONVERSIONS:
		return STANDARD_CONVERSIONS[key]
	
	# Try case-insensitive lookup
	for (std_dim, std_vol), factor in STANDARD_CONVERSIONS.items():
		if std_dim.upper() == dim_uom and std_vol.upper() == vol_uom:
			return factor
	
	# If no conversion found, raise error
	raise ConversionNotFoundError(
		_("No conversion factor found from {0} to {1}. Please create a Dimension Volume UOM Conversion record.").format(
			dimension_uom, volume_uom
		)
	)


def calculate_volume_from_dimensions(
	length: float,
	width: float,
	height: float,
	dimension_uom: Optional[str] = None,
	volume_uom: Optional[str] = None,
	company: Optional[str] = None
) -> float:
	"""
	Calculate volume from dimensions with UOM conversion.
	
	If dimension_uom and volume_uom are provided and different, applies
	conversion factor. Otherwise, returns raw calculation (backward compatible).
	
	Args:
		length: Length in dimension_uom
		width: Width in dimension_uom
		height: Height in dimension_uom
		dimension_uom: UOM of dimensions (optional)
		volume_uom: Target UOM for volume (optional)
		company: Company for warehouse settings defaults (optional)
	
	Returns:
		Volume in volume_uom (or raw calculation if UOMs not provided)
	"""
	# Validate inputs
	if not length or not width or not height:
		return 0.0
	
	length = flt(length)
	width = flt(width)
	height = flt(height)
	
	if length <= 0 or width <= 0 or height <= 0:
		return 0.0
	
	# Calculate raw volume (cubic dimension UOM)
	raw_volume = length * width * height
	
	# If no UOMs provided, return raw calculation (backward compatible)
	if not dimension_uom or not volume_uom:
		return raw_volume
	
	# Get UOMs from warehouse settings if not provided
	if not dimension_uom or not volume_uom:
		try:
			if company:
				settings = frappe.get_cached_doc("Warehouse Settings", company)
				if not dimension_uom:
					dimension_uom = settings.default_dimension_uom
				if not volume_uom:
					volume_uom = settings.default_volume_uom
		except Exception:
			pass
	
	# If still no UOMs, return raw calculation
	if not dimension_uom or not volume_uom:
		return raw_volume
	
	# Try to get conversion factor
	try:
		conversion_factor = get_volume_conversion_factor(
			dimension_uom,
			volume_uom,
			company
		)
		# Apply conversion
		converted_volume = raw_volume * conversion_factor
		return converted_volume
	except ConversionNotFoundError:
		# Log warning but return raw calculation for backward compatibility
		frappe.log_error(
			_("Volume conversion not found: {0} to {1}. Using raw calculation.").format(
				dimension_uom, volume_uom
			),
			"Volume Conversion Warning"
		)
		return raw_volume
	except Exception as e:
		# Log error but return raw calculation for backward compatibility
		frappe.log_error(
			_("Error in volume conversion: {0}").format(str(e)),
			"Volume Conversion Error"
		)
		return raw_volume


def convert_volume(
	value: float,
	from_uom: str,
	to_uom: str,
	company: Optional[str] = None
) -> float:
	"""
	Convert volume from one UOM to another.
	
	Args:
		value: Volume value in from_uom
		from_uom: Source volume UOM
		to_uom: Target volume UOM
		company: Optional company for company-specific conversions
	
	Returns:
		Volume in to_uom
	"""
	if not value or value == 0:
		return 0.0
	
	if not from_uom or not to_uom:
		return flt(value)
	
	# If same UOM, no conversion needed
	if from_uom.upper().strip() == to_uom.upper().strip():
		return flt(value)
	
	# For volume-to-volume conversion, we need to go through dimension UOM
	# This is a simplified approach - in practice, you might need a separate
	# volume-to-volume conversion table
	
	# For now, try to find direct conversion
	try:
		# Try to find conversion in reverse (volume UOM as dimension UOM)
		# This is a workaround - ideally we'd have a separate volume-to-volume conversion
		factor = get_volume_conversion_factor(from_uom, to_uom, company)
		return flt(value) * factor
	except ConversionNotFoundError:
		# If no conversion found, return original value
		frappe.log_error(
			_("Volume-to-volume conversion not found: {0} to {1}").format(
				from_uom, to_uom
			),
			"Volume Conversion Warning"
		)
		return flt(value)


@frappe.whitelist()
def calculate_volume_from_dimensions_api(length, width, height, dimension_uom=None, volume_uom=None, company=None):
	"""
	API wrapper for calculate_volume_from_dimensions.
	This is a whitelisted function that can be called from JavaScript.
	
	Args:
		length: Length value
		width: Width value
		height: Height value
		dimension_uom: UOM of dimensions (optional)
		volume_uom: Target UOM for volume (optional)
		company: Company for warehouse settings defaults (optional)
	
	Returns:
		Dict with 'volume' key containing the calculated volume
	"""
	try:
		volume = calculate_volume_from_dimensions(
			length=float(length) if length else 0,
			width=float(width) if width else 0,
			height=float(height) if height else 0,
			dimension_uom=dimension_uom,
			volume_uom=volume_uom,
			company=company
		)
		return {"volume": volume}
	except Exception as e:
		frappe.log_error(f"Error calculating volume: {str(e)}", "Volume Calculation Error")
		# Return raw calculation as fallback
		length_val = float(length) if length else 0
		width_val = float(width) if width else 0
		height_val = float(height) if height else 0
		return {"volume": length_val * width_val * height_val}

