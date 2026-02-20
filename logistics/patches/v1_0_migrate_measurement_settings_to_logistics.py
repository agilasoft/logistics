# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Migrate measurement default UOMs to Logistics Settings from Transport Capacity Settings
and Warehouse Settings so Logistics Settings is the single source.
Run once after deploying the measurements consolidation (e.g. bench execute).
"""

import frappe


def execute():
	"""Copy default dimension/volume/weight UOMs into Logistics Settings if currently empty."""
	frappe.reload_doctype("Logistics Settings")
	ls = frappe.get_single("Logistics Settings")
	updated = False

	def set_if_empty(field: str, value: str) -> None:
		nonlocal updated
		if value and not getattr(ls, field, None):
			ls.set(field, value)
			updated = True

	# From Transport Capacity Settings
	try:
		tc = frappe.get_single("Transport Capacity Settings")
		set_if_empty("default_dimension_uom", getattr(tc, "default_dimension_uom", None))
		set_if_empty("default_volume_uom", getattr(tc, "default_volume_uom", None))
		set_if_empty("default_weight_uom", getattr(tc, "default_weight_uom", None))
	except Exception:
		pass

	# From first Warehouse Settings if still missing
	if not getattr(ls, "default_dimension_uom", None) or not getattr(ls, "default_volume_uom", None) or not getattr(ls, "default_weight_uom", None):
		try:
			first = frappe.get_all("Warehouse Settings", limit=1)
			if first:
				ws = frappe.get_doc("Warehouse Settings", first[0].name)
				set_if_empty("default_dimension_uom", getattr(ws, "default_dimension_uom", None))
				set_if_empty("default_volume_uom", getattr(ws, "default_volume_uom", None))
				set_if_empty("default_weight_uom", getattr(ws, "default_weight_uom", None))
				set_if_empty("default_chargeable_weight_uom", getattr(ws, "default_chargeable_uom", None))
		except Exception:
			pass

	if updated:
		ls.flags.ignore_permissions = True
		ls.save()
		print("Logistics Settings: migrated default UOMs from Transport Capacity / Warehouse Settings.")
	else:
		print("Logistics Settings: no migration needed (already set or no source values).")
