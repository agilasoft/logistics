# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Populate transport_mode_air / transport_mode_sea on booking & shipment routing legs from Transport Mode.

Replaces v1_0_backfill_routing_leg_transport_mode_flags: Meta has no ``db_table`` on this Frappe version;
use ``frappe.utils.get_table_name`` (same as ORM) for physical table names.
"""

import frappe
from frappe.utils import get_table_name


def execute():
	if not frappe.db.exists("DocType", "Transport Mode"):
		return

	if not frappe.db.table_exists("Transport Mode"):
		return

	tm_table = get_table_name("Transport Mode")

	child_doctypes = [
		"Air Booking Routing Leg",
		"Sea Booking Routing Leg",
		"Air Shipment Routing Leg",
		"Sea Shipment Routing Leg",
	]
	for dt in child_doctypes:
		if not frappe.db.exists("DocType", dt):
			continue
		if not frappe.db.table_exists(dt):
			continue
		leg_table = get_table_name(dt)
		frappe.db.sql(
			f"""
			UPDATE `{leg_table}` AS leg
			LEFT JOIN `{tm_table}` AS tm ON tm.name = leg.mode
			SET leg.transport_mode_air = IFNULL(tm.air, 0),
				leg.transport_mode_sea = IFNULL(tm.sea, 0)
			"""
		)
