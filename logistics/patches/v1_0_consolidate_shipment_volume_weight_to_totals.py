# -*- coding: utf-8 -*-
# Copyright (c) 2026 and contributors
"""Migrate Air Shipment and Sea Shipment: copy volume -> total_volume and weight -> total_weight before removing volume/weight fields."""

import frappe


def execute():
	"""Copy volume and weight into total_volume and total_weight for existing Air Shipment and Sea Shipment docs."""
	for doctype in ("Air Shipment", "Sea Shipment"):
		if not frappe.db.exists("DocType", doctype):
			continue
		table = "tab" + doctype.replace(" ", " ")
		try:
			columns = [c.get("Field") for c in frappe.db.sql("SHOW COLUMNS FROM `{0}`".format(table), as_dict=True)]
			if "volume" in columns and "total_volume" in columns:
				frappe.db.sql("""
					UPDATE `{0}`
					SET total_volume = volume
					WHERE (total_volume IS NULL OR total_volume = 0)
					AND volume IS NOT NULL AND volume != 0
				""".format(table))
			if "weight" in columns and "total_weight" in columns:
				frappe.db.sql("""
					UPDATE `{0}`
					SET total_weight = weight
					WHERE (total_weight IS NULL OR total_weight = 0)
					AND weight IS NOT NULL AND weight != 0
				""".format(table))
			frappe.db.commit()
		except Exception as e:
			frappe.log_error(
				"consolidate_shipment_volume_weight_to_totals ({0}): {1}".format(doctype, str(e)),
				"Patch consolidate_shipment_volume_weight_to_totals",
			)
			raise
