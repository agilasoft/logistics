# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe


def _drop_unique_index_on_route_sequence():
    """Child-table ``unique`` on route_sequence is global across parents; drop it before removing column."""
    table_name = "tabAir Consolidation Routes"
    if not frappe.db.has_column("Air Consolidation Routes", "route_sequence"):
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
                "ALTER TABLE `tabAir Consolidation Routes` DROP INDEX `{}`".format(index_name)
            )


def execute():
    _drop_unique_index_on_route_sequence()
    if frappe.db.has_column("Air Consolidation Routes", "route_sequence"):
        frappe.db.sql("ALTER TABLE `tabAir Consolidation Routes` DROP COLUMN `route_sequence`")
