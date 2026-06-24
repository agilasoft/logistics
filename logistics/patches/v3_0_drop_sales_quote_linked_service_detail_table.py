# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Drop persisted ``tabLinked Service Detail`` rows for Sales Quote.

``Linked Service Detail`` is now a virtual child doctype (``is_virtual: 1``) used
only on Sales Quote. The Services grid is a live view of ``Linked Service``
documents parented via ``parent_booking_type`` / ``parent_booking_name``; child
table rows are no longer persisted.

Run in ``pre_model_sync`` so the table can be dropped before schema sync treats
the child doctype as virtual-only (same pattern as ``Exhibit Docket``).
"""

from __future__ import annotations

import frappe


def execute():
	table = "tabLinked Service Detail"
	if not frappe.db.table_exists(table):
		return
	if frappe.db.has_column("Linked Service Detail", "parenttype"):
		frappe.db.delete("Linked Service Detail", {"parenttype": "Sales Quote"})
	frappe.db.sql_ddl(f"DROP TABLE `{table}`")
	frappe.db.commit()
