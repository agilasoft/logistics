# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, see license.txt

"""
Temperature Validation Utility

Provides global temperature validation logic for minimum and maximum temperature values.
Validates temperatures against configurable limits defined in Logistics Settings.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt
from typing import Optional, Tuple


def get_temperature_limits() -> Tuple[Optional[float], Optional[float]]:
	"""
	Get configured minimum and maximum temperature limits from Logistics Settings.
	
	Returns:
		Tuple of (min_temp, max_temp). Values may be None if not configured.
	"""
	try:
		settings = frappe.get_single("Logistics Settings")
		min_temp = flt(getattr(settings, "min_temp", None)) if hasattr(settings, "min_temp") else None
		max_temp = flt(getattr(settings, "max_temp", None)) if hasattr(settings, "max_temp") else None
		return (min_temp if min_temp != 0 else None, max_temp if max_temp != 0 else None)
	except Exception:
		# If settings don't exist or can't be loaded, return None for both
		return (None, None)


def validate_temperature(
	temperature: float,
	field_label: Optional[str] = None,
	raise_exception: bool = True
) -> Tuple[bool, Optional[str]]:
	"""
	Validate a temperature value against configured global limits.
	
	Args:
		temperature: Temperature value in degrees Celsius to validate
		field_label: Optional label for the temperature field (used in error messages)
		raise_exception: If True, raises frappe.ValidationError when validation fails.
		                If False, returns (is_valid, error_message) tuple.
	
	Returns:
		If raise_exception=False: Tuple of (is_valid, error_message)
		If raise_exception=True: Returns (True, None) or raises exception
	
	Raises:
		frappe.ValidationError: If temperature is out of range and raise_exception=True
	"""
	if temperature is None:
		# None values are not validated (caller should handle required field validation separately)
		return (True, None)
	
	temperature = flt(temperature)
	min_temp, max_temp = get_temperature_limits()
	
	# If limits are not configured, skip validation
	if min_temp is None and max_temp is None:
		return (True, None)
	
	error_message = None
	
	# Check minimum temperature
	if min_temp is not None and temperature < min_temp:
		field_text = f" for {field_label}" if field_label else ""
		error_message = _(
			"Temperature{0} ({1}°C) is below the minimum allowed temperature ({2}°C)."
		).format(field_text, temperature, min_temp)
	
	# Check maximum temperature
	elif max_temp is not None and temperature > max_temp:
		field_text = f" for {field_label}" if field_label else ""
		error_message = _(
			"Temperature{0} ({1}°C) is above the maximum allowed temperature ({2}°C)."
		).format(field_text, temperature, max_temp)
	
	if error_message:
		if raise_exception:
			frappe.throw(error_message, title=_("Temperature Validation Error"))
		return (False, error_message)
	
	return (True, None)


def validate_temperature_range(
	min_temperature: Optional[float],
	max_temperature: Optional[float],
	min_field_label: Optional[str] = None,
	max_field_label: Optional[str] = None,
	raise_exception: bool = True
) -> Tuple[bool, Optional[str]]:
	"""
	Validate a temperature range (min and max) against configured global limits.
	Also validates that min_temperature < max_temperature.
	
	Args:
		min_temperature: Minimum temperature value in degrees Celsius
		max_temperature: Maximum temperature value in degrees Celsius
		min_field_label: Optional label for the minimum temperature field
		max_field_label: Optional label for the maximum temperature field
		raise_exception: If True, raises frappe.ValidationError when validation fails.
		                If False, returns (is_valid, error_message) tuple.
	
	Returns:
		If raise_exception=False: Tuple of (is_valid, error_message)
		If raise_exception=True: Returns (True, None) or raises exception
	
	Raises:
		frappe.ValidationError: If temperature range is invalid and raise_exception=True
	"""
	# Validate that min < max if both are provided
	if min_temperature is not None and max_temperature is not None:
		if flt(min_temperature) >= flt(max_temperature):
			error_message = _("Minimum temperature must be less than maximum temperature.")
			if raise_exception:
				frappe.throw(error_message, title=_("Temperature Validation Error"))
			return (False, error_message)
	
	# Validate minimum temperature against global limits
	if min_temperature is not None:
		is_valid, error_message = validate_temperature(
			min_temperature,
			field_label=min_field_label or "Minimum Temperature",
			raise_exception=False
		)
		if not is_valid:
			if raise_exception:
				frappe.throw(error_message, title=_("Temperature Validation Error"))
			return (False, error_message)
	
	# Validate maximum temperature against global limits
	if max_temperature is not None:
		is_valid, error_message = validate_temperature(
			max_temperature,
			field_label=max_field_label or "Maximum Temperature",
			raise_exception=False
		)
		if not is_valid:
			if raise_exception:
				frappe.throw(error_message, title=_("Temperature Validation Error"))
			return (False, error_message)
	
	return (True, None)
