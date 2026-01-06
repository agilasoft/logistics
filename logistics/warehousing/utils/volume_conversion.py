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
from typing import Optional


class ConversionNotFoundError(Exception):
	"""Raised when a conversion factor cannot be found"""
	pass


def get_volume_conversion_factor(
	dimension_uom: str,
	volume_uom: str,
	company: Optional[str] = None
) -> float:
	"""
	Get conversion factor from dimension UOM to volume UOM.
	
	Retrieves conversion factor from Dimension Volume UOM Conversion records
	in the database. All conversions must be defined in the database.
	
	Args:
		dimension_uom: UOM of dimensions (e.g., "CM", "M")
		volume_uom: UOM of volume (e.g., "CBM", "CFT")
		company: Optional company for company-specific conversions (not currently used)
	
	Returns:
		Conversion factor (float)
	
	Raises:
		ConversionNotFoundError: If conversion not found in database
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
	
	# Try to get conversion from database
	# First try with normalized UOMs
	conversion = None
	try:
		conversion = frappe.db.get_value(
			"Dimension Volume UOM Conversion",
			{
				"dimension_uom": dim_uom,
				"volume_uom": vol_uom,
				"enabled": 1
			},
			"conversion_factor",
			as_dict=True
		)
	except (frappe.DoesNotExistError, frappe.ValidationError):
		# Expected exceptions - no conversion found in database
		pass
	except Exception as e:
		# Log unexpected errors
		frappe.log_error(
			_("Unexpected error fetching conversion from database: {0}").format(str(e)),
			"Volume Conversion Database Error"
		)
	
	# If not found with normalized UOMs, try with original case
	if not conversion or not conversion.get("conversion_factor"):
		try:
			conversion = frappe.db.get_value(
				"Dimension Volume UOM Conversion",
				{
					"dimension_uom": dimension_uom.strip(),
					"volume_uom": volume_uom.strip(),
					"enabled": 1
				},
				"conversion_factor",
				as_dict=True
			)
		except (frappe.DoesNotExistError, frappe.ValidationError):
			pass
		except Exception as e:
			frappe.log_error(
				_("Unexpected error fetching conversion from database: {0}").format(str(e)),
				"Volume Conversion Database Error"
			)
	
	# Return conversion factor if found
	if conversion and conversion.get("conversion_factor"):
		return flt(conversion.get("conversion_factor"))
	
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
	
	# If no UOMs provided (even after checking settings), return raw calculation (backward compatible)
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

