# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Rename Exhibit Lifecycle Stage to shared Lifecycle Stage with module flags."""

from __future__ import annotations

import frappe
from frappe.modules.import_file import import_file_by_path


def execute():
	path = frappe.get_app_path(
		"logistics",
		"logistics",
		"doctype",
		"lifecycle_stage",
		"lifecycle_stage.json",
	)
	import_file_by_path(path, force=True, ignore_version=True, reset_permissions=True)

	old_table = "tabExhibit Lifecycle Stage"
	new_table = "tabLifecycle Stage"

	if (
		frappe.db.exists("DocType", "Exhibit Lifecycle Stage")
		and frappe.db.exists("DocType", "Lifecycle Stage")
	):
		if frappe.db.table_exists(old_table) and frappe.db.table_exists(new_table):
			rows = frappe.db.sql(f"SELECT * FROM `{old_table}`", as_dict=True)
			for row in rows:
				name = row.get("name")
				if not name or frappe.db.exists("Lifecycle Stage", name):
					continue
				frappe.db.sql(
					f"""
					INSERT INTO `{new_table}`
					(name, lifecycle_stage, sort_order, is_closed, description, for_exhibits, for_special_project)
					VALUES (%(name)s, %(lifecycle_stage)s, %(sort_order)s, %(is_closed)s, %(description)s, 1, 1)
					""",
					row,
				)
			frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `{old_table}`")
		frappe.delete_doc("DocType", "Exhibit Lifecycle Stage", force=True, ignore_missing=True)
	elif frappe.db.exists("DocType", "Exhibit Lifecycle Stage"):
		frappe.rename_doc("DocType", "Exhibit Lifecycle Stage", "Lifecycle Stage", force=True)
		if frappe.db.table_exists(old_table) and not frappe.db.table_exists(new_table):
			frappe.db.sql_ddl(f"RENAME TABLE `{old_table}` TO `{new_table}`")

	if frappe.db.table_exists(new_table):
		if frappe.db.has_column("Lifecycle Stage", "for_exhibits"):
			frappe.db.sql(
				f"""
				UPDATE `{new_table}`
				SET for_exhibits = 1
				WHERE IFNULL(for_exhibits, 0) = 0
				"""
			)
		if frappe.db.has_column("Lifecycle Stage", "for_special_project"):
			frappe.db.sql(
				f"""
				UPDATE `{new_table}`
				SET for_special_project = 1
				WHERE IFNULL(for_special_project, 0) = 0
				"""
			)

	frappe.db.commit()
	frappe.clear_cache()
