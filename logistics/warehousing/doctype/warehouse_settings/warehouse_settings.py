# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WarehouseSettings(Document):
	pass


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
