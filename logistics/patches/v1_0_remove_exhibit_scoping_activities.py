# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Remove Exhibit Scoping Activity child DocType and migrate legacy Scoping status."""

from __future__ import annotations

import frappe


def execute():
	if frappe.db.table_exists("tabExhibit") and frappe.db.has_column("Exhibit", "status"):
		frappe.db.sql(
			"""
			UPDATE `tabExhibit`
			SET status = 'Draft'
			WHERE status = 'Scoping'
			"""
		)

	if frappe.db.exists("DocType", "Exhibit Scoping Activity"):
		frappe.delete_doc("DocType", "Exhibit Scoping Activity", force=True, ignore_missing=True)

	for table in ("tabExhibit Scoping Activity", "tabEvent Scoping Activity"):
		if frappe.db.table_exists(table):
			frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `{table}`")

	frappe.db.commit()
	frappe.clear_cache()
