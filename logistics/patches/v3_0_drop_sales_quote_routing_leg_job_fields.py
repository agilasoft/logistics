# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Drop ``job_type`` and ``job_no`` from Sales Quote Routing Leg (jobs resolve via ``sales_quote`` link)."""

from __future__ import unicode_literals

import frappe


def execute():
	if not frappe.db.exists("DocType", "Sales Quote Routing Leg"):
		return
	frappe.db.updatedb("Sales Quote Routing Leg")
	for column in ("job_type", "job_no"):
		_drop_column_if_exists("Sales Quote Routing Leg", column)
	frappe.clear_cache(doctype="Sales Quote Routing Leg")


def _drop_column_if_exists(doctype: str, column: str) -> None:
	if not frappe.db.table_exists(doctype):
		return
	columns = {c.lower() for c in frappe.db.get_table_columns(doctype)}
	if column.lower() not in columns:
		return
	frappe.db.sql_ddl(f"ALTER TABLE `tab{doctype}` DROP COLUMN `{column}`")
