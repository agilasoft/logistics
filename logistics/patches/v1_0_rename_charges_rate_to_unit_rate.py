# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Rename ``rate`` -> ``unit_rate`` on every operational logistics charge child doctype.

Aligns the operational charge tables with ``Sales Quote Charge`` and the weight/qty break
tables (which already use ``unit_rate``). Supersedes the earlier reverse renames
(``v1_0_rename_transport_{job,order}_charges_unit_rate_to_rate``) which standardised on
``rate`` and left an orphan ``unit_rate`` column behind.
"""

import frappe
from frappe.model.utils.rename_field import rename_field


CHARGE_DOCTYPES = (
    "Transport Job Charges",
    "Transport Order Charges",
    "Air Booking Charges",
    "Air Shipment Charges",
    "Air Consolidation Charges",
    "Sea Booking Charges",
    "Sea Shipment Charges",
    "Declaration Charges",
    "Declaration Order Charges",
    "Special Project Charges",
    "MICE Project Charges",
    "Warehouse Job Charges",
    "VAS Order Charges",
    "Inbound Order Charges",
    "Release Order Charges",
    "Transfer Order Charges",
    "Stocktake Order Charges",
    "Periodic Billing Charges",
    "MICE Project Consolidation Charges",
)


def execute():
    for dt in CHARGE_DOCTYPES:
        if not frappe.db.exists("DocType", dt):
            continue

        meta = frappe.get_meta(dt, cached=False)
        has_rate = bool(meta.get_field("rate"))
        has_unit_rate = bool(meta.get_field("unit_rate"))

        # Already renamed (or never had ``rate``); nothing to do.
        if not has_rate or has_unit_rate:
            continue

        table = f"tab{dt}"
        try:
            cols = {row["Field"] for row in frappe.db.sql(f"DESCRIBE `{table}`", as_dict=True)}
        except Exception:
            cols = set()

        # Drop orphan ``unit_rate`` column left over from the previous reverse rename so the
        # subsequent ``rename_field("rate", "unit_rate")`` can recreate the column cleanly.
        if "unit_rate" in cols and "rate" in cols:
            frappe.db.sql(f"ALTER TABLE `{table}` DROP COLUMN `unit_rate`")

        rename_field(dt, "rate", "unit_rate")

    frappe.clear_cache()
    frappe.db.commit()
