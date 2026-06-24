# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Drop ``service_scope`` from Sales Quote charge/Services child tables (lane tag no longer used)."""

from __future__ import unicode_literals

import frappe


_CHILD_TABLES = (
	"Sales Quote Charge",
	"Linked Service Detail",
	"Internal Job Detail",
)


def execute():
	for dt in _CHILD_TABLES:
		if not frappe.db.exists("DocType", dt):
			continue
		frappe.db.updatedb(dt)
		_drop_column_if_exists(dt, "service_scope")
		frappe.clear_cache(doctype=dt)


def _drop_column_if_exists(doctype: str, column: str) -> None:
	if not frappe.db.table_exists(doctype):
		return
	columns = {c.lower() for c in frappe.db.get_table_columns(doctype)}
	if column.lower() not in columns:
		return
	frappe.db.sql_ddl(f"ALTER TABLE `tab{doctype}` DROP COLUMN `{column}`")
