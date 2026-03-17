# Copyright (c) 2026, www.agilasoft.com and contributors
# License: MIT. See LICENSE

"""
Drop leg_order column from routing leg child tables. Order is now determined by idx.
"""

import frappe

ROUTING_LEG_TABLES = [
	"tabAir Booking Routing Leg",
	"tabAir Shipment Routing Leg",
	"tabSea Booking Routing Leg",
	"tabSea Shipment Routing Leg",
	"tabSales Quote Routing Leg",
]


def execute():
	for tab in ROUTING_LEG_TABLES:
		columns = [c[0] for c in frappe.db.sql("SHOW COLUMNS FROM `%s`" % tab)]
		if "leg_order" in columns:
			frappe.db.sql("ALTER TABLE `%s` DROP COLUMN `leg_order`" % tab)
			frappe.db.commit()
