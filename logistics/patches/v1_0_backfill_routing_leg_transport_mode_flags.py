# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Populate transport_mode_air / transport_mode_sea on booking & shipment routing legs from Transport Mode."""

import frappe
from frappe.model.meta import get_meta


def execute():
	if not frappe.db.exists("DocType", "Transport Mode"):
		return

	tm_table = get_meta("Transport Mode").db_table
	if not frappe.db.table_exists(tm_table):
		return

	child_doctypes = [
		"Air Booking Routing Leg",
		"Sea Booking Routing Leg",
		"Air Shipment Routing Leg",
		"Sea Shipment Routing Leg",
	]
	for dt in child_doctypes:
		if not frappe.db.exists("DocType", dt):
			continue
		table = get_meta(dt).db_table
		if not frappe.db.table_exists(table):
			continue
		frappe.db.sql(
			f"""
			UPDATE `{table}` AS leg
			LEFT JOIN `{tm_table}` AS tm ON tm.name = leg.mode
			SET leg.transport_mode_air = IFNULL(tm.air, 0),
				leg.transport_mode_sea = IFNULL(tm.sea, 0)
			"""
		)
