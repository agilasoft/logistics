# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
UOM Conversion Helper for Transport Capacity Management

Provides functions to convert weight, volume, and dimensions between different UOMs
for capacity calculations.
"""

import frappe
from frappe import _
from frappe.utils import flt
from typing import Optional, Dict

# Reuse warehousing volume conversion utilities
try:
	from logistics.warehousing.utils.volume_conversion import (
		calculate_volume_from_dimensions as _warehouse_calculate_volume,
		get_volume_conversion_factor,
		ConversionNotFoundError
	)
except ImportError:
	# Fallback if warehousing module not available
	_warehouse_calculate_volume = None
	get_volume_conversion_factor = None
	ConversionNotFoundError = Exception


def get_default_uoms(company: Optional[str] = None) -> Dict[str, str]:
	"""
	Get default UOMs from Transport Capacity Settings.
	
	Args:
		company: Optional company for company-specific settings
	
	Returns:
		Dictionary with 'weight', 'volume', and 'dimension' UOMs from settings
	
	Raises:
		frappe.ValidationError: If Transport Capacity Settings is not configured
	"""
	try:
		settings = frappe.get_single("Transport Capacity Settings")
		defaults = {}
		
		if hasattr(settings, 'default_weight_uom') and settings.default_weight_uom:
			defaults['weight'] = settings.default_weight_uom
		if hasattr(settings, 'default_volume_uom') and settings.default_volume_uom:
			defaults['volume'] = settings.default_volume_uom
		if hasattr(settings, 'default_dimension_uom') and settings.default_dimension_uom:
			defaults['dimension'] = settings.default_dimension_uom
		
		# Validate that all required UOMs are configured
		missing = []
		if 'weight' not in defaults:
			missing.append('Default Weight UOM')
		if 'volume' not in defaults:
			missing.append('Default Volume UOM')
		if 'dimension' not in defaults:
			missing.append('Default Dimension UOM')
		
		if missing:
			frappe.throw(
				_("Transport Capacity Settings is not fully configured. Please set: {0}").format(", ".join(missing)),
				title=_("Settings Required")
			)
		
		return defaults
	except frappe.DoesNotExistError:
		frappe.throw(
			_("Transport Capacity Settings not found. Please configure default UOMs in Transport Capacity Settings."),
			title=_("Settings Required")
		)
	except Exception as e:
		frappe.log_error(f"Error getting default UOMs: {str(e)}", "UOM Settings Error")
		raise


def get_uom_conversion_factor(from_uom: str, to_uom: str) -> float:
	"""
	Get conversion factor between two UOMs using Frappe's UOM conversion.
	
	Args:
		from_uom: Source UOM
		to_uom: Target UOM
	
	Returns:
		Conversion factor (multiply source value by this to get target value)
	"""
	if not from_uom or not to_uom:
		return 1.0
	
	# Normalize UOMs
	from_uom = str(from_uom).strip().upper()
	to_uom = str(to_uom).strip().upper()
	
	# Same UOM, no conversion needed
	if from_uom == to_uom:
		return 1.0
	
	# Try to get conversion from Frappe UOM conversion table
	try:
		conversion = frappe.db.get_value(
			"UOM Conversion Factor",
			{
				"from_uom": from_uom,
				"to_uom": to_uom
			},
			"value",
			as_dict=True
		)
		
		if conversion and conversion.get("value"):
			return flt(conversion.get("value"))
	except Exception:
		pass
	
	# Try reverse conversion
	try:
		conversion = frappe.db.get_value(
			"UOM Conversion Factor",
			{
				"from_uom": to_uom,
				"to_uom": from_uom
			},
			"value",
			as_dict=True
		)
		
		if conversion and conversion.get("value"):
			return 1.0 / flt(conversion.get("value"))
	except Exception:
		pass
	
	# Hardcoded common conversions as fallback
	common_conversions = {
		# Weight conversions
		('TON', 'KG'): 1000.0,
		('KG', 'TON'): 0.001,
		('LB', 'KG'): 0.453592,
		('KG', 'LB'): 2.20462,
		('G', 'KG'): 0.001,
		('KG', 'G'): 1000.0,
		
		# Volume conversions
		('CFT', 'CBM'): 0.0283168,
		('CBM', 'CFT'): 35.3147,
		('L', 'CBM'): 0.001,
		('CBM', 'L'): 1000.0,
		('ML', 'CBM'): 0.000001,
		('CBM', 'ML'): 1000000.0,
		
		# Dimension conversions
		('M', 'CM'): 100.0,
		('CM', 'M'): 0.01,
		('MM', 'CM'): 0.1,
		('CM', 'MM'): 10.0,
		('FT', 'CM'): 30.48,
		('CM', 'FT'): 0.0328084,
		('IN', 'CM'): 2.54,
		('CM', 'IN'): 0.393701,
	}
	
	key = (from_uom, to_uom)
	if key in common_conversions:
		return common_conversions[key]
	
	# If no conversion found, log warning and return 1.0 (assume same UOM)
	frappe.log_error(
		_("UOM conversion not found: {0} to {1}. Using 1.0 as fallback.").format(
			from_uom, to_uom
		),
		"UOM Conversion Warning"
	)
	return 1.0


def convert_weight(
	value: float,
	from_uom: Optional[str] = None,
	to_uom: Optional[str] = None,
	company: Optional[str] = None
) -> float:
	"""
	Convert weight from one UOM to another.
	
	Args:
		value: Weight value in from_uom
		from_uom: Source UOM (if None, uses default from settings)
		to_uom: Target UOM (if None, uses default from settings)
		company: Optional company for settings
	
	Returns:
		Converted weight value in to_uom
	"""
	if not value or value == 0:
		return 0.0
	
	value = flt(value)
	
	# Get defaults if not provided
	if not from_uom or not to_uom:
		defaults = get_default_uoms(company)
		if not from_uom:
			from_uom = defaults['weight']
		if not to_uom:
			to_uom = defaults['weight']
	
	# Normalize UOMs
	from_uom = str(from_uom).strip().upper()
	to_uom = str(to_uom).strip().upper()
	
	if from_uom == to_uom:
		return value
	
	# Get conversion factor
	factor = get_uom_conversion_factor(from_uom, to_uom)
	return value * factor


def convert_volume(
	value: float,
	from_uom: Optional[str] = None,
	to_uom: Optional[str] = None,
	company: Optional[str] = None
) -> float:
	"""
	Convert volume from one UOM to another.
	
	Args:
		value: Volume value in from_uom
		from_uom: Source UOM (if None, uses default from settings)
		to_uom: Target UOM (if None, uses default from settings)
		company: Optional company for settings
	
	Returns:
		Converted volume value in to_uom
	"""
	if not value or value == 0:
		return 0.0
	
	value = flt(value)
	
	# Get defaults if not provided
	if not from_uom or not to_uom:
		defaults = get_default_uoms(company)
		if not from_uom:
			from_uom = defaults['volume']
		if not to_uom:
			to_uom = defaults['volume']
	
	# Normalize UOMs
	from_uom = str(from_uom).strip().upper()
	to_uom = str(to_uom).strip().upper()
	
	if from_uom == to_uom:
		return value
	
	# Get conversion factor
	factor = get_uom_conversion_factor(from_uom, to_uom)
	return value * factor


def convert_dimension(
	value: float,
	from_uom: Optional[str] = None,
	to_uom: Optional[str] = None,
	company: Optional[str] = None
) -> float:
	"""
	Convert dimension (length/width/height) from one UOM to another.
	
	Args:
		value: Dimension value in from_uom
		from_uom: Source UOM (if None, uses default from settings)
		to_uom: Target UOM (if None, uses default from settings)
		company: Optional company for settings
	
	Returns:
		Converted dimension value in to_uom
	"""
	if not value or value == 0:
		return 0.0
	
	value = flt(value)
	
	# Get defaults if not provided
	if not from_uom or not to_uom:
		defaults = get_default_uoms(company)
		if not from_uom:
			from_uom = defaults['dimension']
		if not to_uom:
			to_uom = defaults['dimension']
	
	# Normalize UOMs
	from_uom = str(from_uom).strip().upper()
	to_uom = str(to_uom).strip().upper()
	
	if from_uom == to_uom:
		return value
	
	# Get conversion factor
	factor = get_uom_conversion_factor(from_uom, to_uom)
	return value * factor


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
	
	Uses warehousing utility if available, otherwise implements basic conversion.
	
	Args:
		length: Length in dimension_uom
		width: Width in dimension_uom
		height: Height in dimension_uom
		dimension_uom: UOM of dimensions (if None, uses default from settings)
		volume_uom: Target UOM for volume (if None, uses default from settings)
		company: Optional company for settings
	
	Returns:
		Volume in volume_uom
	"""
	# Use warehousing utility if available
	if _warehouse_calculate_volume:
		try:
			return _warehouse_calculate_volume(
				length, width, height,
				dimension_uom=dimension_uom,
				volume_uom=volume_uom,
				company=company
			)
		except Exception:
			pass
	
	# Fallback implementation
	if not length or not width or not height:
		return 0.0
	
	length = flt(length)
	width = flt(width)
	height = flt(height)
	
	if length <= 0 or width <= 0 or height <= 0:
		return 0.0
	
	# Get defaults if not provided
	if not dimension_uom or not volume_uom:
		defaults = get_default_uoms(company)
		if not dimension_uom:
			dimension_uom = defaults['dimension']
		if not volume_uom:
			volume_uom = defaults['volume']
	
	# Calculate raw volume (cubic dimension UOM)
	raw_volume = length * width * height
	
	# Try dimension-to-volume conversion
	if get_volume_conversion_factor:
		try:
			conversion_factor = get_volume_conversion_factor(
				dimension_uom,
				volume_uom,
				company
			)
			return raw_volume * conversion_factor
		except Exception:
			pass
	
	# Fallback: convert dimensions to standard, calculate, then convert volume
	# Get default dimension UOM from settings for intermediate conversion
	defaults = get_default_uoms(company)
	standard_dimension_uom = defaults['dimension']
	standard_volume_uom = defaults['volume']
	
	# Convert all dimensions to standard dimension UOM
	length_std = convert_dimension(length, dimension_uom, standard_dimension_uom, company)
	width_std = convert_dimension(width, dimension_uom, standard_dimension_uom, company)
	height_std = convert_dimension(height, dimension_uom, standard_dimension_uom, company)
	
	# Calculate volume in standard dimension UOM³
	volume_std3 = length_std * width_std * height_std
	
	# Convert standard dimension UOM³ to standard volume UOM
	# This requires a conversion factor based on the standard dimension UOM
	# For CM -> CBM: divide by 1,000,000; for M -> CBM: multiply by 1
	if standard_dimension_uom.upper() == 'CM':
		# CM³ to CBM: divide by 1,000,000
		volume_std = volume_std3 / 1000000.0
	elif standard_dimension_uom.upper() == 'M':
		# M³ to CBM: same (1 m³ = 1 CBM)
		volume_std = volume_std3
	else:
		# For other dimension UOMs, convert to CM first, then to CBM
		length_cm = convert_dimension(length_std, standard_dimension_uom, 'CM', company)
		width_cm = convert_dimension(width_std, standard_dimension_uom, 'CM', company)
		height_cm = convert_dimension(height_std, standard_dimension_uom, 'CM', company)
		volume_cm3 = length_cm * width_cm * height_cm
		volume_std = volume_cm3 / 1000000.0
	
	# Convert from standard volume UOM to target volume UOM
	if volume_uom.upper() == standard_volume_uom.upper():
		return volume_std
	else:
		return convert_volume(volume_std, standard_volume_uom, volume_uom, company)


def standardize_capacity_value(
	value: float,
	uom: Optional[str],
	capacity_type: str,
	company: Optional[str] = None
) -> float:
	"""
	Convert capacity value to standard UOM for calculations.
	
	Args:
		value: Capacity value
		uom: Current UOM (if None, assumes already in standard UOM)
		capacity_type: 'weight', 'volume', or 'dimension'
		company: Optional company for settings
	
	Returns:
		Value in standard UOM
	"""
	if not value or value == 0:
		return 0.0
	
	if not uom:
		return flt(value)
	
	defaults = get_default_uoms(company)
	standard_uom = defaults.get(capacity_type)
	if not standard_uom:
		frappe.throw(
			_("Default {0} UOM not configured in Transport Capacity Settings").format(capacity_type.title()),
			title=_("Settings Required")
		)
	
	if capacity_type == 'weight':
		return convert_weight(value, uom, standard_uom, company)
	elif capacity_type == 'volume':
		return convert_volume(value, uom, standard_uom, company)
	elif capacity_type == 'dimension':
		return convert_dimension(value, uom, standard_uom, company)
	else:
		return flt(value)
