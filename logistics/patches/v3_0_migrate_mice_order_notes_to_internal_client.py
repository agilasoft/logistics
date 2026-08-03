# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Migrate MICE Order ``notes`` into ``internal_notes`` / ``client_notes``.

Aligns MICE Order More Info notes with MICE Job (side-by-side Text Editors).
Existing Small Text ``notes`` values are copied into ``internal_notes``.
"""

from __future__ import unicode_literals

import frappe


def execute():
	if not frappe.db.table_exists("tabMICE Order"):
		return

	columns = set(frappe.db.get_table_columns("MICE Order") or [])

	if "internal_notes" not in columns:
		frappe.db.sql_ddl("ALTER TABLE `tabMICE Order` ADD COLUMN `internal_notes` longtext")
	if "client_notes" not in columns:
		frappe.db.sql_ddl("ALTER TABLE `tabMICE Order` ADD COLUMN `client_notes` longtext")

	if "notes" in columns:
		frappe.db.sql(
			"""
			UPDATE `tabMICE Order`
			SET internal_notes = notes
			WHERE (internal_notes IS NULL OR internal_notes = '')
			  AND notes IS NOT NULL AND notes != ''
			"""
		)
		frappe.db.sql_ddl("ALTER TABLE `tabMICE Order` DROP COLUMN `notes`")

	frappe.reload_doc("mice", "doctype", "mice_order")
	frappe.clear_cache(doctype="MICE Order")
	frappe.db.commit()
