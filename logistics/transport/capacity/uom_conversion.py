# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
UOM conversion: thin wrapper around logistics.utils.measurements.

All default UOMs and conversion logic live in measurements.py (Logistics Settings).
This module exists for backward compatibility for transport capacity callers.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt
from typing import Optional

from logistics.utils.measurements import (
	get_default_uoms,
	get_uom_conversion_factor,
	convert_weight as _convert_weight,
	convert_volume as _convert_volume,
	convert_dimension as _convert_dimension,
	calculate_volume_from_dimensions as _calculate_volume_from_dimensions,
)


def convert_weight(
	value: float,
	from_uom: Optional[str] = None,
	to_uom: Optional[str] = None,
	company: Optional[str] = None,
) -> float:
	"""Delegates to logistics.utils.measurements.convert_weight."""
	return _convert_weight(value=value, from_uom=from_uom, to_uom=to_uom, company=company)


def convert_volume(
	value: float,
	from_uom: Optional[str] = None,
	to_uom: Optional[str] = None,
	company: Optional[str] = None,
) -> float:
	"""Delegates to logistics.utils.measurements.convert_volume."""
	return _convert_volume(value=value, from_uom=from_uom, to_uom=to_uom, company=company)


def convert_dimension(
	value: float,
	from_uom: Optional[str] = None,
	to_uom: Optional[str] = None,
	company: Optional[str] = None,
) -> float:
	"""Delegates to logistics.utils.measurements.convert_dimension."""
	return _convert_dimension(value=value, from_uom=from_uom, to_uom=to_uom, company=company)


def calculate_volume_from_dimensions(
	length: float,
	width: float,
	height: float,
	dimension_uom: Optional[str] = None,
	volume_uom: Optional[str] = None,
	company: Optional[str] = None,
) -> float:
	"""Delegates to logistics.utils.measurements.calculate_volume_from_dimensions."""
	return _calculate_volume_from_dimensions(
		length=length,
		width=width,
		height=height,
		dimension_uom=dimension_uom,
		volume_uom=volume_uom,
		company=company,
	)


def standardize_capacity_value(
	value: float,
	uom: Optional[str],
	capacity_type: str,
	company: Optional[str] = None,
) -> float:
	"""
	Convert capacity value to standard UOM for calculations.
	Uses Logistics Settings (via measurements.get_default_uoms).
	"""
	if not value or value == 0:
		return 0.0
	if not uom:
		return flt(value)
	defaults = get_default_uoms(company)
	standard_uom = defaults.get(capacity_type)
	if not standard_uom:
		frappe.throw(
			_("Default {0} UOM not configured in Logistics Settings.").format(capacity_type.title()),
			title=_("Settings Required"),
		)
	if capacity_type == "weight":
		return convert_weight(value, uom, standard_uom, company)
	if capacity_type == "volume":
		return convert_volume(value, uom, standard_uom, company)
	if capacity_type == "dimension":
		return convert_dimension(value, uom, standard_uom, company)
	return flt(value)
