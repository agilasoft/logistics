# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Add child-link columns on tables that were not created as child tables.

Schema sync does not add ``parent`` when a table already exists. Opening a
parent then fails with unknown column ``parent``. Job Task is repaired by
``v3_0_repair_job_task_parent_columns``. This patch covers the other tables.
"""

from __future__ import annotations

import frappe

from logistics.child_link_schema import (
	REPAIRS,
	add_column_clauses,
	missing_child_link_columns,
	relink_statement,
	should_relink_legacy_rows,
)


def _columns(repair) -> set[str]:
	# table_exists prefixes "tab" itself. Pass the DocType name.
	if not frappe.db.table_exists(repair.table_exists_argument(), cached=False):
		return set()
	return {row["Field"] for row in frappe.db.sql(f"DESCRIBE `{repair.table}`", as_dict=True)}


def execute():
	for repair in REPAIRS:
		columns = _columns(repair)
		if not columns:
			continue

		missing = missing_child_link_columns(columns)
		if missing:
			clauses = add_column_clauses(missing, frappe.db.VARCHAR_LEN)
			frappe.db.sql_ddl(f"ALTER TABLE `{repair.table}` " + ", ".join(clauses))
			columns.update(missing)
			print(f"{repair.doctype}: added {', '.join(missing)}")

		has_parent_index = frappe.db.sql(
			f"SHOW INDEX FROM `{repair.table}` WHERE Key_name = 'parent'"
		)
		if "parent" in columns and not has_parent_index:
			frappe.db.sql_ddl(f"ALTER TABLE `{repair.table}` ADD INDEX `parent` (`parent`)")

		if should_relink_legacy_rows(repair, columns):
			frappe.db.sql(relink_statement(repair))
			print(f"{repair.doctype}: linked standalone rows")

		frappe.db.commit()
		frappe.clear_cache(doctype=repair.doctype)
