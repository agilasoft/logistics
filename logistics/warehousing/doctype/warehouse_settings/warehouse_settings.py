# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WarehouseSettings(Document):
	pass


@frappe.whitelist()
def get_default_uoms(company=None):
	"""
	Return default UOMs from Warehouse Settings for the given company (or first record).
	Used by Warehouse Contract Item and other warehousing doctypes when defaulting weight/volume/chargeable UOM.
	Returns dict with keys: volume, weight, chargeable (and optionally dimension).
	"""
	try:
		if company:
			settings = frappe.get_doc("Warehouse Settings", company)
		else:
			first = frappe.get_all("Warehouse Settings", limit=1)
			if not first:
				return None
			settings = frappe.get_doc("Warehouse Settings", first[0].name)
		out = {}
		if getattr(settings, "default_volume_uom", None):
			out["volume"] = settings.default_volume_uom
		if getattr(settings, "default_weight_uom", None):
			out["weight"] = settings.default_weight_uom
		if getattr(settings, "default_chargeable_uom", None):
			out["chargeable"] = settings.default_chargeable_uom
		if getattr(settings, "default_dimension_uom", None):
			out["dimension"] = settings.default_dimension_uom
		return out if out else None
	except Exception:
		return None


@frappe.whitelist()
def calculate_volume_from_dimensions(length, width, height, dimension_uom=None, volume_uom=None, company=None):
	"""
	Calculate volume from dimensions with UOM conversion.
	This is a server-side method that can be called from JavaScript.
	"""
	from logistics.warehousing.utils.volume_conversion import calculate_volume_from_dimensions as calc_volume
	
	try:
		volume = calc_volume(
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
		length = float(length) if length else 0
		width = float(width) if width else 0
		height = float(height) if height else 0
		return {"volume": length * width * height}
