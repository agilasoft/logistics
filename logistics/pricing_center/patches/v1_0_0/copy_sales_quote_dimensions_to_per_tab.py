# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, see license.txt

"""
Migration: Copy existing weight, volume, chargeable (and UOMs) from top-level Sales Quote
into per-tab fields (sea_*, air_*, transport_*, warehouse_*) for existing documents.
Run after Sales Quote DocType has been updated with per-tab dimension fields.
"""

import frappe
from frappe.utils import flt


def execute():
	"""Copy old weight/volume/chargeable into per-tab fields for existing Sales Quotes."""
	if not frappe.db.table_exists("Sales Quote"):
		return

	# Check if new columns exist (DocType was migrated)
	try:
		frappe.db.sql("""
			SELECT name, weight, weight_uom, volume, volume_uom, chargeable, chargeable_uom
			FROM `tabSales Quote`
			WHERE name IS NOT NULL
			LIMIT 1
		""")
	except Exception:
		return  # Old columns may not exist or table structure different

	# Check if per-tab columns exist
	columns = [d.get("Field") for d in frappe.db.sql("SHOW COLUMNS FROM `tabSales Quote`", as_dict=True)]
	per_tab_cols = ["transport_weight", "sea_weight", "air_weight", "warehouse_weight"]
	if not all(c in columns for c in per_tab_cols):
		return  # Per-tab fields not yet in schema; skip (patch can run again after migrate)

	updated = 0
	for name, in frappe.db.sql("SELECT name FROM `tabSales Quote`"):
		row = frappe.db.get_value(
			"Sales Quote",
			name,
			["weight", "weight_uom", "volume", "volume_uom", "chargeable", "chargeable_uom"],
			as_dict=True,
		)
		if not row:
			continue
		# Only copy if at least one value is set and per-tab fields are empty
		has_old = any([
			row.get("weight") is not None and flt(row.get("weight")) != 0,
			row.get("volume") is not None and flt(row.get("volume")) != 0,
			row.get("chargeable") is not None and flt(row.get("chargeable")) != 0,
		])
		if not has_old:
			continue
		# Copy to all four per-tab field sets
		frappe.db.sql("""
			UPDATE `tabSales Quote`
			SET
				transport_weight = COALESCE(transport_weight, weight),
				transport_weight_uom = COALESCE(transport_weight_uom, weight_uom),
				transport_volume = COALESCE(transport_volume, volume),
				transport_volume_uom = COALESCE(transport_volume_uom, volume_uom),
				transport_chargeable = COALESCE(transport_chargeable, chargeable),
				transport_chargeable_uom = COALESCE(transport_chargeable_uom, chargeable_uom),
				sea_weight = COALESCE(sea_weight, weight),
				sea_weight_uom = COALESCE(sea_weight_uom, weight_uom),
				sea_volume = COALESCE(sea_volume, volume),
				sea_volume_uom = COALESCE(sea_volume_uom, volume_uom),
				sea_chargeable = COALESCE(sea_chargeable, chargeable),
				sea_chargeable_uom = COALESCE(sea_chargeable_uom, chargeable_uom),
				air_weight = COALESCE(air_weight, weight),
				air_weight_uom = COALESCE(air_weight_uom, weight_uom),
				air_volume = COALESCE(air_volume, volume),
				air_volume_uom = COALESCE(air_volume_uom, volume_uom),
				air_chargeable = COALESCE(air_chargeable, chargeable),
				air_chargeable_uom = COALESCE(air_chargeable_uom, chargeable_uom),
				warehouse_weight = COALESCE(warehouse_weight, weight),
				warehouse_weight_uom = COALESCE(warehouse_weight_uom, weight_uom),
				warehouse_volume = COALESCE(warehouse_volume, volume),
				warehouse_volume_uom = COALESCE(warehouse_volume_uom, volume_uom),
				warehouse_chargeable = COALESCE(warehouse_chargeable, chargeable),
				warehouse_chargeable_uom = COALESCE(warehouse_chargeable_uom, chargeable_uom)
			WHERE name = %(name)s
		""", {"name": name})
		updated += 1

	frappe.db.commit()
	if updated:
		print(f"Sales Quote per-tab dimensions: copied old weight/volume/chargeable into per-tab fields for {updated} document(s).")
