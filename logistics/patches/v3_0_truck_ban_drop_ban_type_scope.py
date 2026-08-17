# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Drop unused ban_type / scope fields from Truck Ban Constraint after schema sync."""

from __future__ import unicode_literals

import frappe


def execute():
	if not frappe.db.exists("DocType", "Truck Ban Constraint"):
		return
	frappe.db.updatedb("Truck Ban Constraint")
	for column in ("ban_type", "scope_level", "scope_location"):
		_drop_column_if_exists("Truck Ban Constraint", column)
	frappe.clear_cache(doctype="Truck Ban Constraint")


def _drop_column_if_exists(doctype: str, column: str) -> None:
	if not frappe.db.table_exists(doctype):
		return
	columns = {c.lower() for c in frappe.db.get_table_columns(doctype)}
	if column.lower() not in columns:
		return
	frappe.db.sql_ddl(f"ALTER TABLE `tab{doctype}` DROP COLUMN `{column}`")
