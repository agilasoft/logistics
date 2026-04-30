# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Shared capacity / utilization for Sea Booking Containers and Sea Freight Containers (Sea Consolidation pattern)."""

import frappe
from frappe.utils import flt


def sync_sea_freight_container_child_rows(parent_doc):
	"""Set max_weight / max_volume / utilization_percentage on each container row from Container Type + cargo fields."""
	if getattr(frappe.flags, "in_import", False) or getattr(frappe.flags, "in_migrate", False):
		return
	for row in getattr(parent_doc, "containers", None) or []:
		_sync_one_container_row(row)


def _sync_one_container_row(row):
	ctype = getattr(row, "type", None)
	max_w = flt(0)
	max_v = flt(0)
	if ctype:
		ct = frappe.db.get_value(
			"Container Type",
			ctype,
			["max_gross_weight"],
			as_dict=True,
		)
		if ct and ct.get("max_gross_weight") is not None:
			max_w = flt(ct.max_gross_weight)
		if frappe.db.has_column("Container Type", "max_volume"):
			mv = frappe.db.get_value("Container Type", ctype, "max_volume")
			if mv is not None:
				max_v = flt(mv)
	row.max_weight = max_w
	row.max_volume = max_v
	wic = flt(getattr(row, "weight_in_container", 0) or 0)
	vic = flt(getattr(row, "volume_in_container", 0) or 0)
	parts = []
	if max_w > 0:
		parts.append(wic / max_w * 100.0)
	if max_v > 0:
		parts.append(vic / max_v * 100.0)
	row.utilization_percentage = max(parts) if parts else flt(0)
