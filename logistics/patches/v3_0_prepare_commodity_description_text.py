# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Widen Commodity.description before DocType sync.

The field was Data (varchar 140) and is now Text. HS chapter descriptions in
demo/customer data are longer than 140 characters, so MariaDB rejects
`MODIFY description varchar(140)` with 1406 Data too long (e.g. row 24).
"""

import frappe

_TEXT_TYPES = ("text", "mediumtext", "longtext")


def execute():
	if not frappe.db.table_exists("Commodity"):
		return
	if not frappe.db.has_column("Commodity", "description"):
		return

	col_type = (frappe.db.get_column_type("Commodity", "description") or "").lower()
	base_type = col_type.split("(", 1)[0].strip()
	if base_type in _TEXT_TYPES:
		return

	if frappe.db.db_type == "postgres":
		frappe.db.sql_ddl('ALTER TABLE "tabCommodity" ALTER COLUMN "description" TYPE text')
	else:
		frappe.db.sql_ddl(
			"ALTER TABLE `tabCommodity` "
			"MODIFY `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
		)
	frappe.db.commit()
