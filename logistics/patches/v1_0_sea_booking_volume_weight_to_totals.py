# -*- coding: utf-8 -*-
# Copyright (c) 2026 and contributors
"""Migrate Sea Booking: copy volume -> total_volume and weight -> total_weight before removing volume/weight fields."""

import frappe


def execute():
	"""Copy volume and weight into total_volume and total_weight for existing Sea Booking docs."""
	if not frappe.db.exists("DocType", "Sea Booking"):
		return
	table = "tabSea Booking"
	try:
		columns = [c.get("Field") for c in frappe.db.sql("SHOW COLUMNS FROM `{0}`".format(table), as_dict=True)]
		if "volume" in columns and "total_volume" in columns:
			frappe.db.sql("""
				UPDATE `tabSea Booking`
				SET total_volume = volume
				WHERE volume IS NOT NULL
			""")
		if "weight" in columns and "total_weight" in columns:
			frappe.db.sql("""
				UPDATE `tabSea Booking`
				SET total_weight = weight
				WHERE weight IS NOT NULL
			""")
		frappe.db.commit()
	except Exception as e:
		frappe.log_error(
			"sea_booking_volume_weight_to_totals: " + str(e),
			"Patch sea_booking_volume_weight_to_totals",
		)
		raise
