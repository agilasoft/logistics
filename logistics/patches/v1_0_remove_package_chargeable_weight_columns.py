# Copyright (c) 2025, www.agilasoft.com and contributors
# License: MIT. See LICENSE

"""
Drop chargeable_weight and chargeable_weight_uom columns from package child tables.
Chargeable weight is now computed and stored only on parent doctypes.
"""

import frappe

PACKAGE_TABLES = [
    "tabAir Booking Packages",
    "tabAir Shipment Packages",
    "tabSea Booking Packages",
    "tabSea Freight Packages",
    "tabTransport Order Package",
    "tabTransport Job Package",
]


def execute():
    for table in PACKAGE_TABLES:
        if not frappe.db.table_exists(table):
            continue
        for col in ("chargeable_weight", "chargeable_weight_uom"):
            if frappe.db.has_column(table, col):
                frappe.db.sql("ALTER TABLE `{0}` DROP COLUMN `{1}`".format(table, col))
                frappe.db.commit()
                print(f"Dropped column '{col}' from {table}")
