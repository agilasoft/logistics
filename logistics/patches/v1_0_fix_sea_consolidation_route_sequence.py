# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe


def _drop_unique_index_on_route_sequence():
    table_name = "tabSea Consolidation Routes"
    if not frappe.db.has_column("Sea Consolidation Routes", "route_sequence"):
        return
    indexes = frappe.db.sql(
        """
        SELECT DISTINCT INDEX_NAME
        FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND column_name = 'route_sequence'
          AND non_unique = 0
        """,
        (table_name,),
        as_dict=True,
    )

    for row in indexes:
        index_name = row.get("INDEX_NAME")
        if index_name and index_name != "PRIMARY":
            frappe.db.sql(
                "ALTER TABLE `tabSea Consolidation Routes` DROP INDEX `{}`".format(index_name)
            )


def _resequence_all_routes():
    if not frappe.db.has_column("Sea Consolidation Routes", "route_sequence"):
        return
    parents = frappe.get_all(
        "Sea Consolidation Routes",
        fields=["parent"],
        distinct=True,
        filters={"parenttype": "Sea Consolidation"},
    )

    for p in parents:
        rows = frappe.get_all(
            "Sea Consolidation Routes",
            filters={
                "parenttype": "Sea Consolidation",
                "parent": p.parent,
            },
            fields=["name", "idx"],
            order_by="idx asc",
        )

        for i, row in enumerate(rows, 1):
            frappe.db.set_value(
                "Sea Consolidation Routes",
                row.name,
                "route_sequence",
                i,
                update_modified=False,
            )


def execute():
    _drop_unique_index_on_route_sequence()
    _resequence_all_routes()
