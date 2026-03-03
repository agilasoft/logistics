# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Migrate routing mode from Select to Link Transport Mode. Ensure Transport Mode records exist."""

import frappe


def execute():
    ensure_transport_modes()
    # Existing mode values (Air, Sea, Road, Rail, Sea, Air from previous Select) are valid Transport Mode names.
    # Old values SEA, AIR are migrated in SQL for child tables.
    migrate_legacy_mode_values()


def ensure_transport_modes():
    """Create Air, Sea, Road, Rail Transport Mode records if missing."""
    if not frappe.db.exists("DocType", "Transport Mode"):
        return
    modes = [
        {"mode_code": "Air", "mode_name": "Air", "primary_document": "Air Shipment", "description": "Air freight"},
        {"mode_code": "Sea", "mode_name": "Sea", "primary_document": "Sea Shipment", "description": "Sea freight"},
        {"mode_code": "Road", "mode_name": "Road", "primary_document": "Transport Job", "description": "Road transport"},
        {"mode_code": "Rail", "mode_name": "Rail", "primary_document": "Transport Job - Rail", "description": "Rail transport"},
        {"mode_code": "Inland Water", "mode_name": "Inland Water", "primary_document": "Transport Job - Inland Water", "description": "Inland waterway transport"},
        {"mode_code": "Cable", "mode_name": "Cable", "primary_document": "Transport Job - Cable", "description": "Cable transport"},
        {"mode_code": "Pipeline", "mode_name": "Pipeline", "primary_document": "Transport Job - Pipeline", "description": "Pipeline transport"},
        {"mode_code": "Space", "mode_name": "Space", "primary_document": "Transport Job - Space", "description": "Space transport"},
        # Legacy values - preserve existing data
        {"mode_code": "Inland Waterway", "mode_name": "Inland Waterway", "primary_document": "Transport Job - Inland Waterway", "description": "Inland waterway"},
        {"mode_code": "Other", "mode_name": "Other", "primary_document": "Transport Job - Other", "description": "Other transport mode"},
    ]
    for m in modes:
        if not frappe.db.exists("Transport Mode", m["mode_code"]):
            doc = frappe.new_doc("Transport Mode")
            doc.update(m)
            doc.insert()


def migrate_legacy_mode_values():
    """Map old Select values (SEA, AIR) to Transport Mode names (Sea, Air)."""
    tables = [
        ("Sea Booking Routing Leg", "tabSea Booking Routing Leg"),
        ("Sea Shipment Routing Leg", "tabSea Shipment Routing Leg"),
        ("Air Booking Routing Leg", "tabAir Booking Routing Leg"),
        ("Air Shipment Routing Leg", "tabAir Shipment Routing Leg"),
        ("Freight Routing Items", "tabFreight Routing Items"),
        ("Sales Quote Routing Leg", "tabSales Quote Routing Leg"),
    ]
    for doctype, table in tables:
        if not frappe.db.table_exists(table):
            continue
        # Migrate SEA -> Sea, AIR -> Air (legacy values from before mode options change)
        frappe.db.sql(
            f"UPDATE `{table}` SET mode = 'Sea' WHERE mode = 'SEA'"
        )
        frappe.db.sql(
            f"UPDATE `{table}` SET mode = 'Air' WHERE mode = 'AIR'"
        )
    frappe.db.commit()
