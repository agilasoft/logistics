# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe


MASTER_DOCTYPES = (
    "Address",
    "Contact",
    "Consignee",
    "Shipper",
    "Freight Agent",
    "Broker",
    "Freight Consolidator",
    "Transport Company",
    "Transport Vehicle",
    "Transport Terminal",
    "Container Depot",
    "Container Freight Station",
    "Cargo Terminal Operator",
    "Vehicle Make",
    "Vehicle Type",
    "Storage Facility",
    "Economic Zone",
    "Transport Mode",
    "Release Type",
    "Exporter Category",
    "IATA Rate Class",
    "ULD Type",
    "Time Zone",
)


def execute():
    """Backfill Is Active for masters that now include the field."""
    for doctype in MASTER_DOCTYPES:
        if not frappe.db.table_exists(doctype):
            continue
        if not frappe.db.has_column(doctype, "is_active"):
            continue

        frappe.db.sql(
            f"""
            UPDATE `tab{doctype}`
            SET is_active = 1
            WHERE IFNULL(is_active, 0) = 0
            """
        )

    frappe.db.commit()
