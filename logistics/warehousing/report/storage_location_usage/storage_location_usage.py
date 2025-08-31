# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

# import frappe


# Copyright (c) 2025
# License: MIT

from __future__ import unicode_literals
import frappe


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data = get_data(filters)

    chart = make_chart(data)
    summary = make_summary(data)

    # Script Report return signature: columns, data, message, chart, summary
    return columns, data, None, chart, summary


# -------------------------------------------------------------------
# Columns
# -------------------------------------------------------------------
def get_columns():
    return [
        {
            "label": "Site",
            "fieldname": "site",
            "fieldtype": "Link",
            "options": "Storage Location Configurator",
            "width": 120,
        },
        {
            "label": "Building",
            "fieldname": "building",
            "fieldtype": "Link",
            "options": "Storage Location Configurator",
            "width": 120,
        },
        {
            "label": "Zone",
            "fieldname": "zone",
            "fieldtype": "Link",
            "options": "Storage Location Configurator",
            "width": 110,
        },
        {
            "label": "Aisle",
            "fieldname": "aisle",
            "fieldtype": "Link",
            "options": "Storage Location Configurator",
            "width": 90,
        },
        {
            "label": "Bay",
            "fieldname": "bay",
            "fieldtype": "Link",
            "options": "Storage Location Configurator",
            "width": 80,
        },
        {
            "label": "Level",
            "fieldname": "level",
            "fieldtype": "Link",
            "options": "Storage Location Configurator",
            "width": 80,
        },
        {
            "label": "Storage Location",
            "fieldname": "storage_location",
            "fieldtype": "Link",
            "options": "Storage Location",
            "width": 220,
        },
        {
            "label": "Location Code",
            "fieldname": "location_code",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": "Storage Type",
            "fieldname": "storage_type",
            "fieldtype": "Link",
            "options": "Storage Type",
            "width": 130,
        },
        {
            "label": "Qty",
            "fieldname": "qty",
            "fieldtype": "Float",
            "width": 100,
            "precision": 2,
        },
        {
            "label": "In Use",
            "fieldname": "in_use",
            "fieldtype": "Check",
            "width": 90,
        },
    ]


# -------------------------------------------------------------------
# Data
# -------------------------------------------------------------------
def get_data(filters):
    # Build WHERE from level filters
    where_clauses = []
    params = {}

    for f in ("site", "building", "zone", "aisle", "bay", "level", "storage_type"):
        if filters.get(f):
            where_clauses.append(f"sl.`{f}` = %({f})s")
            params[f] = filters.get(f)

    where_sql = "WHERE 1=1"
    if where_clauses:
        where_sql += " AND " + " AND ".join(where_clauses)

    # Aggregate balance per storage_location from Warehouse Stock Ledger
    # NOTE: field is spelled 'quantiy' in your DocType — we use that.
    sql = f"""
        SELECT
            sl.name                   AS storage_location,
            sl.site,
            sl.building,
            sl.zone,
            sl.aisle,
            sl.bay,
            sl.level,
            sl.location_code,
            sl.storage_type,
            COALESCE(bal.qty, 0)      AS qty,
            CASE
                WHEN COALESCE(bal.qty, 0) <> 0 THEN 1
                ELSE 0
            END                       AS in_use
        FROM `tabStorage Location` sl
        LEFT JOIN (
            SELECT
                storage_location,
                SUM(COALESCE(quantiy, 0)) AS qty
            FROM `tabWarehouse Stock Ledger`
            GROUP BY storage_location
        ) bal
            ON bal.storage_location = sl.name
        {where_sql}
        ORDER BY
            sl.site, sl.building, sl.zone, sl.aisle, sl.bay, sl.level, sl.location_code, sl.name
    """

    return frappe.db.sql(sql, params, as_dict=True)


# -------------------------------------------------------------------
# Chart + Summary
# -------------------------------------------------------------------
def _is_in_use(val):
    # Accept 1/0, True/False, "Yes"/"No", etc.
    return 1 if (val in (1, "1", True, "Yes", "Y", "In Use")) else 0


def make_chart(data):
    total = len(data) or 0
    in_use = sum(_is_in_use(d.get("in_use")) for d in data)
    available = max(total - in_use, 0)

    return {
        "data": {
            "labels": ["In Use", "Available"],
            "datasets": [{"name": "Locations", "values": [in_use, available]}],
        },
        "type": "donut",
        "height": 260,
    }


def make_summary(data):
    total = len(data) or 0
    in_use = sum(_is_in_use(d.get("in_use")) for d in data)
    available = max(total - in_use, 0)
    util = (in_use / total * 100.0) if total else 0.0

    return [
        {"label": "Total Locations", "value": total, "indicator": "blue", "datatype": "Int"},
        {"label": "In Use", "value": in_use, "indicator": "red", "datatype": "Int"},
        {"label": "Available", "value": available, "indicator": "green", "datatype": "Int"},
        {"label": "Utilization", "value": util, "indicator": "orange", "datatype": "Percent", "precision": 1},
    ]
