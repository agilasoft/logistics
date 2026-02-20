# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Volume conversion: thin wrapper around logistics.utils.measurements.

All logic lives in measurements.py. This module exists for backward compatibility.
"""

from __future__ import annotations

import frappe
from typing import Optional

from logistics.utils.measurements import (
	ConversionNotFoundError,
	get_volume_conversion_factor,
	calculate_volume_from_dimensions,
)
from logistics.utils import measurements as _measurements


def convert_volume(
	value: float,
	from_uom: str,
	to_uom: str,
	company: Optional[str] = None,
) -> float:
	"""Volume-to-volume conversion. Delegates to measurements.convert_volume."""
	return _measurements.convert_volume(
		value=value,
		from_uom=from_uom,
		to_uom=to_uom,
		company=company,
	)


@frappe.whitelist()
def calculate_volume_from_dimensions_api(length, width, height, dimension_uom=None, volume_uom=None, company=None):
	"""Whitelisted API. Delegates to measurements.calculate_volume_from_dimensions_api."""
	import frappe
	return _measurements.calculate_volume_from_dimensions_api(
		length=length,
		width=width,
		height=height,
		dimension_uom=dimension_uom,
		volume_uom=volume_uom,
		company=company,
	)
