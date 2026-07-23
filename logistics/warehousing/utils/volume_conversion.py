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


def sync_row_volume_from_dimensions(
	row,
	parent_doctype: Optional[str] = None,
	company: Optional[str] = None,
) -> Optional[float]:
	"""
	Always set row.volume from L×W×H when dimensions are present.

	Used by WMS order line items so save cannot leave a stale volume after
	dimensions were edited (or restored via fetch_from).
	"""
	from frappe.utils import flt

	length = flt(getattr(row, "length", None))
	width = flt(getattr(row, "width", None))
	height = flt(getattr(row, "height", None))
	if length <= 0 or width <= 0 or height <= 0:
		return None

	dimension_uom = getattr(row, "dimension_uom", None)
	volume_uom = getattr(row, "volume_uom", None)

	if not dimension_uom or not volume_uom:
		try:
			if not company:
				parent_dt = parent_doctype or getattr(row, "parenttype", None)
				parent = getattr(row, "parent", None)
				if parent_dt and parent:
					company = frappe.get_cached_value(parent_dt, parent, "company")
			if not company:
				company = frappe.defaults.get_user_default("Company")
			if company:
				warehouse_settings = frappe.get_cached_doc("Warehouse Settings", company)
				if not dimension_uom:
					dimension_uom = warehouse_settings.default_dimension_uom
				if not volume_uom:
					volume_uom = warehouse_settings.default_volume_uom
				if dimension_uom and not getattr(row, "dimension_uom", None):
					row.dimension_uom = dimension_uom
				if volume_uom and not getattr(row, "volume_uom", None):
					row.volume_uom = volume_uom
		except Exception:
			pass

	calculated_volume = calculate_volume_from_dimensions(
		length=length,
		width=width,
		height=height,
		dimension_uom=dimension_uom,
		volume_uom=volume_uom,
		company=company,
	)
	row.volume = calculated_volume
	return calculated_volume


def sync_items_volume_from_dimensions(doc, child_table: str = "items") -> None:
	"""Sync volume on all child measurement rows. Call from parent validate()."""
	company = getattr(doc, "company", None)
	for row in getattr(doc, child_table, None) or []:
		sync_row_volume_from_dimensions(
			row,
			parent_doctype=getattr(doc, "doctype", None),
			company=company,
		)
