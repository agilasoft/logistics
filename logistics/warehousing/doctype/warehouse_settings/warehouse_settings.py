# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WarehouseSettings(Document):
	pass


@frappe.whitelist()
def get_default_uoms(company=None):
	"""
	Return default UOMs from Logistics Settings (single source).
	Backward-compatible shape: volume, weight, chargeable, dimension.
	"""
	from logistics.utils.measurements import get_default_uoms as _get_default_uoms
	out = _get_default_uoms(company=company)
	return {
		"volume": out.get("volume"),
		"weight": out.get("weight"),
		"chargeable": out.get("chargeable_weight"),
		"dimension": out.get("dimension"),
	}


@frappe.whitelist()
def calculate_volume_from_dimensions(length, width, height, dimension_uom=None, volume_uom=None, company=None):
	"""
	Calculate volume from dimensions. Delegates to logistics.utils.measurements.
	Returns dict with "volume" key for client scripts.
	"""
	from logistics.utils.measurements import calculate_volume_from_dimensions_api
	return calculate_volume_from_dimensions_api(
		length=length,
		width=width,
		height=height,
		dimension_uom=dimension_uom,
		volume_uom=volume_uom,
		company=company,
	)
