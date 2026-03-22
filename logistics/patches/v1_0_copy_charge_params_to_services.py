# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Copy charge parameters from Sales Quote Charge to Sales Quote Service."""

import frappe

PARAM_FIELDS = [
    "air_house_type", "sea_house_type", "load_type", "direction",
    "origin_port", "destination_port", "airline", "freight_agent",
    "freight_agent_sea", "shipping_line", "transport_mode",
    "transport_template", "vehicle_type", "container_type",
    "location_type", "location_from", "location_to", "pick_mode", "drop_mode",
    "customs_authority", "declaration_type", "customs_broker", "customs_charge_category",
]


def execute():
    """Copy params from first charge per service_type to corresponding service row."""
    if not frappe.db.table_exists("Sales Quote Service") or not frappe.db.table_exists("Sales Quote Charge"):
        return

    meta_svc = frappe.get_meta("Sales Quote Service")
    meta_chg = frappe.get_meta("Sales Quote Charge")
    valid_fields = [f for f in PARAM_FIELDS if meta_svc.has_field(f) and meta_chg.has_field(f)]
    if not valid_fields:
        return

    services = frappe.get_all(
        "Sales Quote Service",
        filters={"parenttype": "Sales Quote"},
        fields=["name", "parent", "service_type"] + valid_fields,
    )
    for svc in services:
        if not svc.service_type:
            continue
        # Skip if service already has origin_port (or first param) - already migrated
        if svc.get("origin_port") or svc.get("load_type") or svc.get("transport_template"):
            continue

        first_chg = frappe.db.get_value(
            "Sales Quote Charge",
            {"parent": svc.parent, "parenttype": "Sales Quote", "service_type": svc.service_type},
            fieldname=valid_fields,
            as_dict=True,
            order_by="idx",
        )
        if not first_chg:
            continue

        updates = {f: first_chg.get(f) for f in valid_fields if first_chg.get(f) is not None}
        if not updates:
            continue

        frappe.db.set_value("Sales Quote Service", svc.name, updates, update_modified=False)

    frappe.db.commit()
