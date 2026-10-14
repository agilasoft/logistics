# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Add child-table columns to ``tabJob Task``.

Job Task was created as a standalone DocType, then turned into the child table
on bookings and jobs. Migrate updates the DocType, but it does not add
``parent`` to a table that already exists. Loading Air Booking then fails with
``Unknown column 'parent'``.
"""

from __future__ import annotations

import frappe

from logistics.job_management.job_task_child_schema import (
	TABLE,
	add_column_clauses,
	missing_child_link_columns,
	relink_statement,
	should_relink_legacy_rows,
)


def _columns() -> set[str]:
	if not frappe.db.table_exists(TABLE):
		return set()
	return {row["Field"] for row in frappe.db.sql(f"DESCRIBE `{TABLE}`", as_dict=True)}


def execute():
	columns = _columns()
	if not columns:
		return

	missing = missing_child_link_columns(columns)
	if missing:
		clauses = add_column_clauses(missing, frappe.db.VARCHAR_LEN)
		frappe.db.sql_ddl(f"ALTER TABLE `{TABLE}` " + ", ".join(clauses))
		columns.update(missing)
		print(f"Job Task: added {', '.join(missing)}")

	has_parent_index = frappe.db.sql(f"SHOW INDEX FROM `{TABLE}` WHERE Key_name = 'parent'")
	if "parent" in columns and not has_parent_index:
		frappe.db.sql_ddl(f"ALTER TABLE `{TABLE}` ADD INDEX `parent` (`parent`)")

	if should_relink_legacy_rows(columns):
		frappe.db.sql(relink_statement(has_sequence="sequence" in columns))
		print("Job Task: linked standalone rows onto their jobs")

	frappe.db.commit()
	frappe.clear_cache(doctype="Job Task")
