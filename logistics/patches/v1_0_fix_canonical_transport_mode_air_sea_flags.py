# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Set ``air`` / ``sea`` on canonical Transport Mode masters (Air, Sea).

Routing legs hide/show vessel vs flight fields via ``transport_mode_air`` / ``transport_mode_sea``,
derived from these checkboxes. Defaults left them off for legacy installs; see routing leg ``depends_on``.

After fixing masters, refresh hidden flags on all booking/shipment routing legs (same join as
``v1_0_backfill_routing_leg_transport_mode_flags_v2``).
"""

import frappe
from frappe.utils import get_table_name


def execute():
	if not frappe.db.exists("DocType", "Transport Mode"):
		return

	# Canonical modes created by install_transport_modes (name = mode_code)
	if frappe.db.exists("Transport Mode", "Air"):
		frappe.db.set_value("Transport Mode", "Air", "air", 1)
	if frappe.db.exists("Transport Mode", "Sea"):
		frappe.db.set_value("Transport Mode", "Sea", "sea", 1)

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

	frappe.db.commit()
