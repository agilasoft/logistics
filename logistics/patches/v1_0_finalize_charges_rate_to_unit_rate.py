# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Finalize the ``rate`` -> ``unit_rate`` migration on every charge child table.

Inspects the *database* (not the cached doctype meta) for each operational charge
child table and:

* if both ``rate`` and ``unit_rate`` columns exist and ``unit_rate`` is empty,
  copies the ``rate`` values into ``unit_rate`` and drops the legacy ``rate``
  column;
* if only the legacy ``rate`` column exists, renames it to ``unit_rate``;
* otherwise (only ``unit_rate`` left), does nothing.

This patch supersedes ``v1_0_rename_charges_rate_to_unit_rate`` for installations
where that patch was a no-op because the in-memory DocType meta already pointed
at ``unit_rate`` (e.g. the ``*_charges.json`` rename had already been deployed
before the patch ran).
"""

import frappe


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


def _table_columns(table: str) -> set:
    try:
        rows = frappe.db.sql(f"DESCRIBE `{table}`", as_dict=True)
    except Exception:
        return set()
    return {r["Field"] for r in rows}


def execute():
    for dt in CHARGE_DOCTYPES:
        if not frappe.db.exists("DocType", dt):
            continue

        table = f"tab{dt}"
        cols = _table_columns(table)
        if not cols:
            continue

        has_rate = "rate" in cols
        has_unit_rate = "unit_rate" in cols

        if has_rate and has_unit_rate:
            # Copy any non-zero ``rate`` values into ``unit_rate`` when the latter
            # is empty, then drop the legacy column.
            frappe.db.sql(
                f"""
                UPDATE `{table}`
                SET `unit_rate` = `rate`
                WHERE (`unit_rate` IS NULL OR `unit_rate` = 0)
                  AND `rate` IS NOT NULL
                  AND `rate` <> 0
                """
            )
            frappe.db.commit()
            frappe.db.sql_ddl(f"ALTER TABLE `{table}` DROP COLUMN `rate`")
        elif has_rate and not has_unit_rate:
            # Plain rename when only the legacy column survived.
            frappe.db.sql_ddl(
                f"ALTER TABLE `{table}` CHANGE COLUMN `rate` `unit_rate` DECIMAL(18,9) NOT NULL DEFAULT 0"
            )

    frappe.clear_cache()
    frappe.db.commit()
